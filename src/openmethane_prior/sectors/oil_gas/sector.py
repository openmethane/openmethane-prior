#
# Copyright 2023 The Superpower Institute Ltd.
#
# This file is part of OpenMethane.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import datetime
import numpy as np
import xarray as xr

from openmethane_prior.lib import (
    logger,
    PriorSectorConfig,
    kg_to_period_cell_flux,
)
from openmethane_prior.data_sources.inventory import get_sector_emissions_by_code, inventory_data_source
from openmethane_prior.data_sources.safeguard import (
    filter_facilities,
    safeguard_mechanism_data_source,
    safeguard_locations_data_source,
)
from openmethane_prior.lib.sector.au_sector import AustraliaPriorSector
from openmethane_prior.lib.units import days_in_period

from .emission_sources.all_sources import all_emission_sources

logger = logger.get_logger(__name__)

def process_emissions(sector: AustraliaPriorSector, sector_config: PriorSectorConfig, prior_ds: xr.Dataset):
    config = sector_config.prior_config

    # read the total emissions over the sector (in kg)
    emissions_inventory = sector_config.data_manager.get_asset(inventory_data_source).data
    sector_total_emissions = get_sector_emissions_by_code(
        emissions_inventory=emissions_inventory,
        start_date=config.start_date,
        end_date=config.end_date,
        category_codes=sector.unfccc_categories,
    )

    # create a DataFrame with all potential methane emission sources in the sector
    emission_sources_df = all_emission_sources(
        data_manager=sector_config.data_manager,
        prior_config=config,
    )

    # add a column for the emission from each source, using NaN to indicate
    # "not yet allocated" instead of "no emission"
    emission_sources_df["emissions_quantity"] = np.nan

    # identify Safeguard Mechanism facilities in this sector which reported
    # emissions during the period of interest
    safeguard_facilities_df = sector_config.data_manager.get_asset(safeguard_mechanism_data_source).data
    sector_facilities_df = filter_facilities(
        facility_df=safeguard_facilities_df,
        anzsic_codes=sector.anzsic_codes,
        period=(config.start_date.date(), config.end_date.date()),
    )
    logger.info(f"Found {len(sector_facilities_df)} Safeguard facilities, totalling {sector_facilities_df['ch4_kg'].sum() / 1e9:.2f}Mt annual CH4")

    # scale annual safeguard emissions to the total amount for the period (kg),
    # the same unit output from get_sector_emissions_by_code
    year_end = datetime.date(config.start_date.year + 1, config.start_date.month, config.start_date.day)
    year_days = (year_end - config.start_date.date()).days
    annual_fraction = days_in_period(config.start_date.date(), config.end_date.date()) / year_days
    sector_facilities_df["ch4_kg"] *= annual_fraction
    logger.info(f"{sector_facilities_df['ch4_kg'].sum():.2f}kg total CH4 reported in sectors {sector.anzsic_codes} in the period")

    # Safeguard locations dataset tells us where we can find locations of
    # wells and sites that correspond to a Safeguard facility
    facility_locations_df = sector_config.data_manager.get_asset(safeguard_locations_data_source).data
    located_facilities_df = sector_facilities_df.merge(
        facility_locations_df,
        left_on="facility_name",
        right_on="safeguard_facility_name",
    )

    unallocated_sector_emissions = sector_total_emissions
    for idx_fac, facility in sector_facilities_df.iterrows():
        locations = located_facilities_df[located_facilities_df["facility_name"] == facility.facility_name]

        # build a list of emission sources related to this SGM facility
        facility_emission_sources_mask = emission_sources_df["data_source"] == False
        for idx_loc, location in located_facilities_df.loc[locations.index].iterrows():
            location_exact_match = (emission_sources_df["data_source"] == location["data_source_name"]) \
                & (emission_sources_df["data_source_id"] == location["data_source_id"])
            location_group_match = (emission_sources_df["data_source"] == location["data_source_name"]) \
                & (emission_sources_df["group_id"] == location["data_source_id"])
            location_emission_sources_mask = location_exact_match | location_group_match

            # add the emission sources for this location
            facility_emission_sources_mask |= location_emission_sources_mask

            # if location_emission_sources_mask.sum() == 0:
            #     logger.debug(f"No sources found for location {facility.facility_name} {location.data_source_name}:{location.data_source_id}")

        # if no locations can be related to an SGM facility, that's a problem
        # TODO: find a method for locating "27 Gas Supply" sites
        if facility_emission_sources_mask.sum() == 0:
            logger.warning(f"No sources found for facility '{facility.facility_name}', unable to allocate {facility['ch4_kg']:.2f}kg CH4")
            continue

        # allocate SGM emissions for this facility equally to its locations
        # TODO: apply weighting to emissions distribution based on site_type
        emission_sources_df.loc[facility_emission_sources_mask, "emissions_quantity"] = facility["ch4_kg"] / facility_emission_sources_mask.sum()
        unallocated_sector_emissions -= facility["ch4_kg"]

    logger.debug(f"{emission_sources_df['emissions_quantity'].sum():.2f}kg allocated to SGM facilities")

    # emission sources don't include a methane quantity or proxy, so naively
    # distribute sector emissions evenly to each active source that hasn't
    # already had emissions allocated to it
    unallocated_emission_sources_mask = np.isnan(emission_sources_df["emissions_quantity"])
    emission_sources_df.loc[unallocated_emission_sources_mask, "emissions_quantity"] = unallocated_sector_emissions / unallocated_emission_sources_mask.sum()

    logger.debug(f"{unallocated_emission_sources_mask.sum()} / {len(emission_sources_df)} unallocated sources ({100 * unallocated_emission_sources_mask.sum() / len(emission_sources_df):.1f}%)")
    logger.debug(f"{unallocated_sector_emissions:.2f} / {sector_total_emissions:.2f}kg unallocated emissions ({100 * unallocated_sector_emissions / sector_total_emissions:.1f}%)")

    domain_grid = config.domain_grid()

    methane = np.zeros(domain_grid.shape)

    for index, site in emission_sources_df.iterrows():
        # geometry type for each site will determine how to allocate emissions
        # to the grid
        geom_type = emission_sources_df.geom_type[index] if type(emission_sources_df.geom_type[index]) == str \
                    else emission_sources_df.geom_type[index].iloc[0]
        if geom_type == "Point":
            cell_x, cell_y, cell_valid = domain_grid.xy_to_cell_index(site["geometry"].x, site["geometry"].y)
            if cell_valid:
                methane[cell_y, cell_x] += site["emissions_quantity"]
        else:
            raise NotImplementedError("Allocating emissions to non-point geometry is not implemented")

    return kg_to_period_cell_flux(methane, config)


sector = AustraliaPriorSector(
    name="oil_gas",
    emission_category="anthropogenic",
    unfccc_categories=["1.B.2"], # Fugitive emissions from fuels, Oil and Natural Gas
    anzsic_codes=[
        "07", # Oil and Gas Extraction
        "17", # Petroleum and Coal Product Manufacturing
        # TODO: https://github.com/openmethane/openmethane-prior/issues/165
        "27", # Gas Supply
    ],
    cf_standard_name="extraction_production_and_transport_of_fuel",
    create_estimate=process_emissions,
)
