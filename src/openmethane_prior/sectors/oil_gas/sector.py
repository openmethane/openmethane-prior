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
from openmethane_prior.data_sources.au_shapes import au_shapes_states_data_source
from openmethane_prior.data_sources.inventory import (
    get_sector_emissions_by_code,
    inventory_data_source,
    qld_inventory_data_source,
)
from openmethane_prior.data_sources.nightlights import night_lights_data_source
from openmethane_prior.data_sources.safeguard import (
    filter_facilities,
    safeguard_mechanism_data_source,
    safeguard_locations_data_source,
)
from openmethane_prior.lib.sector.au_sector import AustraliaPriorSector
from openmethane_prior.lib.units import days_in_period

from .emission_source import allocate_emissions_to_sources
from .emission_sources.all_sources import all_emission_sources
from .safeguard import gas_supply_emissions, get_sector_safeguard_facilities

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
    logger.debug(f"Total sector emissions: {sector_total_emissions / 1e6:.2f} kt in the period")

    qld_inventory = sector_config.data_manager.get_asset(qld_inventory_data_source).data
    qld_total_emissions = get_sector_emissions_by_code(
        emissions_inventory=qld_inventory,
        start_date=config.start_date,
        end_date=config.end_date,
        category_codes=sector.unfccc_categories,
    )
    logger.debug(f"QLD sector emissions: {qld_total_emissions / 1e6:.2f} kt ({100 * qld_total_emissions / sector_total_emissions:.1f}% of sector total)")

    # create a DataFrame with all potential methane emission sources in the sector
    emission_sources_df = all_emission_sources(
        data_manager=sector_config.data_manager,
        prior_config=config,
        anzsic_codes=sector.anzsic_codes,
    )

    # add a column for the emission from each source, using NaN to indicate
    # "not yet allocated" instead of "no emission"
    emission_sources_df["emissions_quantity"] = np.nan

    # identify Safeguard Mechanism facilities in this sector which reported
    # emissions during the period of interest
    safeguard_facilities_da = sector_config.data_manager.get_asset(safeguard_mechanism_data_source)
    sector_facilities_df = get_sector_safeguard_facilities(
        safeguard_facilities_df=safeguard_facilities_da.data,
        anzsic_codes=sector.anzsic_codes,
        period=(config.start_date.date(), config.end_date.date()),
    )

    total_allocated_emissions = 0

    # allocate Gas Supply sub-sector first, this is based on nighttime lights
    # and not point emissions like the rest of the sources.
    au_states_df = sector_config.data_manager.get_asset(au_shapes_states_data_source).data
    night_lights = sector_config.data_manager.get_asset(night_lights_data_source).data
    # filter out facilities with more than one state, ie "NSW; VIC"
    gas_supply_facilities_mask = sector_facilities_df["anzsic_code"].str.startswith("27") \
                                 & sector_facilities_df["state"].isin(au_states_df["short_name"])
    gas_supply_nd = gas_supply_emissions(
        domain_grid=config.domain_grid(),
        facilities_df=sector_facilities_df[gas_supply_facilities_mask],
        au_states=au_states_df,
        nightlights=night_lights,
    )
    total_allocated_emissions += float(gas_supply_nd.sum())
    logger.debug(f"{total_allocated_emissions / 1e6:.2f} kt allocated to SGM gas supply facilities")

    # Remove gas supply facilities since they've been spatialised
    sector_facilities_df = sector_facilities_df[~gas_supply_facilities_mask]

    # Safeguard locations dataset tells us where we can find locations of
    # wells and sites that correspond to a Safeguard facility
    facility_locations_df = sector_config.data_manager.get_asset(safeguard_locations_data_source).data
    located_facilities_df = sector_facilities_df.merge(
        facility_locations_df,
        left_on="facility_name",
        right_on="safeguard_facility_name",
    )

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

        # if no locations can be related to an SGM facility, that's a problem
        if facility_emission_sources_mask.sum() == 0:
            logger.warning(f"No sources found for facility '{facility.facility_name}', unable to allocate {facility['ch4_kg']:.2f}kg CH4")
            continue

        # allocate SGM emissions for this facility equally to its locations
        allocate_emissions_to_sources(
            sources_df=emission_sources_df,
            sources_mask=facility_emission_sources_mask,
            emission_mass=facility["ch4_kg"],
        )

    total_allocated_emissions += emission_sources_df['emissions_quantity'].sum()
    logger.debug(f"{total_allocated_emissions / 1e6:.2f} kt allocated to SGM facilities")

    # find all QLD emission sources so we can allocate the QLD inventory
    qld_sources_mask = emission_sources_df["state"] == "QLD"
    qld_sources = emission_sources_df[qld_sources_mask]

    # calculate remaining QLD inventory that hasn't been allocated
    qld_unallocated_emissions = qld_total_emissions - qld_sources["emissions_quantity"].sum()

    # distribute the remaining emissions among the remaining sources in QLD
    qld_unallocated_emission_sources_mask = np.isnan(emission_sources_df["emissions_quantity"]) & qld_sources_mask
    allocate_emissions_to_sources(
        sources_df=emission_sources_df,
        sources_mask=qld_unallocated_emission_sources_mask,
        emission_mass=qld_unallocated_emissions,
    )
    total_allocated_emissions += qld_unallocated_emissions

    logger.debug(f"{qld_unallocated_emission_sources_mask.sum()} / {qld_sources_mask.sum()} unallocated QLD sources ({100 * qld_unallocated_emission_sources_mask.sum() / len(emission_sources_df):.1f}%)")
    logger.debug(f"{qld_unallocated_emissions / 1e6 :.2f} / {qld_total_emissions / 1e6:.2f} kt unallocated QLD emissions ({100 * qld_unallocated_emissions / qld_total_emissions:.1f}%)")

    # emission sources don't include a methane quantity or proxy, so naively
    # distribute sector emissions evenly to each active source that hasn't
    # already had emissions allocated to it
    unallocated_emission_sources_mask = np.isnan(emission_sources_df["emissions_quantity"])
    unallocated_national_emissions = sector_total_emissions - total_allocated_emissions
    allocate_emissions_to_sources(
        sources_df=emission_sources_df,
        sources_mask=unallocated_emission_sources_mask,
        emission_mass=unallocated_national_emissions,
    )

    logger.debug(f"{unallocated_emission_sources_mask.sum()} / {len(emission_sources_df)} unallocated sources ({100 * unallocated_emission_sources_mask.sum() / len(emission_sources_df):.1f}%)")
    logger.debug(f"{unallocated_national_emissions / 1e6:.2f} / {sector_total_emissions / 1e6:.2f} kt unallocated emissions ({100 * unallocated_national_emissions / sector_total_emissions:.1f}%)")

    domain_grid = config.domain_grid()

    methane_nd = np.zeros(domain_grid.shape)
    methane_nd += gas_supply_nd

    for index, site in emission_sources_df.iterrows():
        # geometry type for each site will determine how to allocate emissions
        # to the grid
        geom_type = emission_sources_df.geom_type[index] if type(emission_sources_df.geom_type[index]) == str \
                    else emission_sources_df.geom_type[index].iloc[0]
        if geom_type == "Point":
            cell_x, cell_y, cell_valid = domain_grid.xy_to_cell_index(site["geometry"].x, site["geometry"].y)
            if cell_valid:
                methane_nd[cell_y, cell_x] += site["emissions_quantity"]
        else:
            raise NotImplementedError("Allocating emissions to non-point geometry is not implemented")

    return kg_to_period_cell_flux(methane_nd, config)


sector = AustraliaPriorSector(
    name="oil_gas",
    emission_category="anthropogenic",
    unfccc_categories=["1.B.2"], # Fugitive emissions from fuels, Oil and Natural Gas
    anzsic_codes=[
        "07", # Oil and Gas Extraction
        "17", # Petroleum and Coal Product Manufacturing
        "27", # Gas Supply
        "502", # Pipeline and other transport
    ],
    cf_standard_name="extraction_production_and_transport_of_fuel",
    create_estimate=process_emissions,
)
