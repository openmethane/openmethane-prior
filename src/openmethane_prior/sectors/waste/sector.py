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
import numpy as np
import xarray as xr

from openmethane_prior.data_sources.inventory import get_sector_emissions_by_code, inventory_data_source
from openmethane_prior.data_sources.safeguard import (
    get_sector_safeguard_facilities,
    safeguard_mechanism_data_source,
    safeguard_locations_data_source,
)
from openmethane_prior.lib import (
    kg_to_period_cell_flux,
    logger,
    PriorSectorConfig,
)
from openmethane_prior.lib.sector.au_sector import AustraliaPriorSector

from .emission_sources import waste_emission_sources

logger = logger.get_logger(__name__)


def process_emissions(
        sector: AustraliaPriorSector,
        sector_config: PriorSectorConfig,
        prior_ds: xr.Dataset,
):
    config = sector_config.prior_config
    domain_grid = config.domain().grid

    # load the national inventory data, ready to calculate sectoral totals
    emissions_inventory = sector_config.data_manager.get_asset(inventory_data_source).data
    sector_total_emissions = get_sector_emissions_by_code(
        emissions_inventory=emissions_inventory,
        start_date=config.start_date,
        end_date=config.end_date,
        category_codes=sector.unfccc_categories,
    )

    # find all known locations for waste sector emissions
    emission_sources_df = waste_emission_sources(
        config=config,
        data_manager=sector_config.data_manager,
        anzsic_codes=sector.anzsic_codes,
    )

    # NPI facilities have no emissions_quantity estimate, so add one by
    # taking the average emission from CT emission sources
    emission_quantity_mean = emission_sources_df["emissions_quantity"].mean()
    emission_sources_df.loc[np.isnan(emission_sources_df["emissions_quantity"]), "emissions_quantity"] = emission_quantity_mean

    # identify Safeguard Mechanism facilities in this sector which reported
    # emissions during the period of interest
    safeguard_facilities_da = sector_config.data_manager.get_asset(safeguard_mechanism_data_source)
    sector_facilities_df = get_sector_safeguard_facilities(
        safeguard_facilities_df=safeguard_facilities_da.data,
        anzsic_codes=sector.anzsic_codes,
        period=(config.start_date.date(), config.end_date.date()),
    )
    if len(sector_facilities_df) == 0:
        logger.info(f"No Safeguard facilities found for the period")
    else:
        logger.info(f"{sector_facilities_df['ch4_kg'].sum() / 1e6:.2f} kt total Safeguard emissions in the period in sectors: {','.join(sector.anzsic_codes)}")

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
        # note: may be overkill, most waste sources only have a single location
        facility_mask = emission_sources_df["data_source"] == False
        for idx_loc, location in located_facilities_df.loc[locations.index].iterrows():
            # add the emission sources for this location
            facility_mask |= (emission_sources_df["data_source"] == location["data_source_name"]) \
                & (emission_sources_df["data_source_id"] == location["data_source_id"])

        # if no locations can be related to an SGM facility, that's a problem
        if facility_mask.sum() == 0:
            logger.warning(f"No sources found for facility '{facility.facility_name}', unable to allocate {facility['ch4_kg']:.2f}kg CH4")
            continue

        # allocate SGM emissions for this facility equally to its locations
        emission_sources_df.loc[facility_mask, "inventory_quantity"] = facility["ch4_kg"] / facility_mask.sum()

    allocated_emissions = emission_sources_df["inventory_quantity"].sum()
    logger.debug(f"{allocated_emissions / 1e6:.2f} kt allocated to SGM facilities")

    unallocated_emission_sources_mask = np.isnan(emission_sources_df["inventory_quantity"])
    unallocated_national_emissions = sector_total_emissions - allocated_emissions
    unallocated_emissions_scale = unallocated_national_emissions / emission_sources_df[unallocated_emission_sources_mask]["emissions_quantity"].sum()

    logger.debug(f"{unallocated_emission_sources_mask.sum()} / {len(emission_sources_df)} unallocated sources ({100 * unallocated_emission_sources_mask.sum() / len(emission_sources_df):.1f}%)")
    logger.debug(f"{unallocated_national_emissions / 1e6:.2f} / {sector_total_emissions / 1e6:.2f} kt unallocated emissions ({100 * unallocated_national_emissions / sector_total_emissions:.1f}%)")

    # scale site emissions so the aggregate matches the inventory total
    emission_sources_df.loc[unallocated_emission_sources_mask, "inventory_quantity"] = (
        unallocated_emissions_scale * emission_sources_df.loc[unallocated_emission_sources_mask, "emissions_quantity"]
    )

    methane_nd = np.zeros(domain_grid.shape)

    logger.debug(f"Allocating point source emissions")
    cell_x, cell_y, cell_valid = domain_grid.xy_to_cell_index(emission_sources_df["geometry"].x, emission_sources_df["geometry"].y)
    np.add.at(methane_nd, (cell_y[cell_valid], cell_x[cell_valid]), emission_sources_df[cell_valid]["inventory_quantity"])

    return kg_to_period_cell_flux(methane_nd, config)


sector = AustraliaPriorSector(
    name="waste",
    emission_category="anthropogenic",
    unfccc_categories=["5"], # Waste
    anzsic_codes=[
        "28", # Water Supply, Sewerage and Drainage Services
        "29", # Waste Collection, Treatment and Disposal Services
    ],
    cf_standard_name="waste_treatment_and_disposal",
    create_estimate=process_emissions,
)
