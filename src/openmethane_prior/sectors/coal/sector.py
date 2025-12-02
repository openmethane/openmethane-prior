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
import pandas as pd
import xarray as xr

from openmethane_prior.data_sources.safeguard import (
    safeguard_locations_data_source,
    safeguard_mechanism_data_source,
)
from openmethane_prior.lib import (
    DataSource,
    logger,
    PriorSectorConfig,
    kg_to_period_cell_flux,
)
from openmethane_prior.data_sources.inventory import get_sector_emissions_by_code, inventory_data_source
from openmethane_prior.lib.sector.au_sector import AustraliaPriorSector
from openmethane_prior.lib.units import days_in_period

from .data import coal_facilities_data_source, filter_coal_facilities
from .safeguard_coal import allocate_safeguard_facility_emissions

logger = logger.get_logger(__name__)


def process_emissions(sector: AustraliaPriorSector, sector_config: PriorSectorConfig, prior_ds: xr.Dataset):
    config = sector_config.prior_config

    # prepare a grid to allocate emissions
    domain_grid = config.domain_grid()
    methane = np.zeros(domain_grid.shape)

    safeguard_mechanism_asset = sector_config.data_manager.get_asset(safeguard_mechanism_data_source)
    facility_locations_asset = sector_config.data_manager.get_asset(safeguard_locations_data_source)
    coal_facilities_asset = sector_config.data_manager.get_asset(coal_facilities_data_source)

    safeguard_facilities, safeguard_locations, safeguard_gridded_ch4 = allocate_safeguard_facility_emissions(
        config=config,
        anzsic_codes=["060"],
        safeguard_facilities_asset=safeguard_mechanism_asset,
        facility_locations_asset=facility_locations_asset,
        reference_data_asset=coal_facilities_asset,
    )

    # add safeguard emissions to our gridded sector emissions
    methane += safeguard_gridded_ch4

    # read the total emissions over the sector (in kg)
    emissions_inventory = sector_config.data_manager.get_asset(inventory_data_source).data
    sector_total_emissions = get_sector_emissions_by_code(
        emissions_inventory=emissions_inventory,
        start_date=config.start_date,
        end_date=config.end_date,
        category_codes=sector.unfccc_categories,
    )

    # SGM emissions have been allocated, find the remaining inventory
    safeguard_allocated_emissions = safeguard_facilities["ch4_kg"].sum() * (days_in_period(config.start_date, config.end_date) / 365)
    sector_unallocated_emissions = sector_total_emissions - safeguard_allocated_emissions

    # select gas and year
    coal_ch4_period = filter_coal_facilities(
        coal_facilities_asset.data,
        (config.start_date, config.end_date),
    )

    # remove facilities that were allocated Safeguard emissions
    coal_unallocated = coal_ch4_period[~coal_ch4_period["source_name"].isin(safeguard_locations["data_source_id"])]

    # normalise remaining emissions to match remaining inventory
    coal_unallocated.loc[:, "emissions_quantity"] *= (
        sector_unallocated_emissions / coal_unallocated["emissions_quantity"].sum()
    )

    unallocated_facilities_gridded = np.zeros(domain_grid.shape)
    for _, facility in coal_unallocated.iterrows():
        cell_x, cell_y, cell_valid = domain_grid.lonlat_to_cell_index(facility["lon"], facility["lat"])

        if cell_valid:
            unallocated_facilities_gridded[cell_y, cell_x] += facility["emissions_quantity"]

    methane += kg_to_period_cell_flux(unallocated_facilities_gridded, config)

    return methane


sector = AustraliaPriorSector(
    name="coal",
    emission_category="anthropogenic",
    unfccc_categories=["1.B.1"], # Fugitive emissions from fuels, Solid Fuels
    anzsic_codes=["06"], # Coal mining
    cf_standard_name="extraction_production_and_transport_of_fuel",
    create_estimate=process_emissions,
)
