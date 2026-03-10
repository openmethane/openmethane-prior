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

from openmethane_prior.data_sources.inventory import get_sector_emissions_by_code, inventory_data_source
from openmethane_prior.data_sources.safeguard import safeguard_mechanism_data_source, safeguard_locations_data_source
from openmethane_prior.lib.data_manager.parsers import parse_csv
from openmethane_prior.lib import (
    DataSource,
    days_in_period,
    logger,
    PriorSectorConfig,
    kg_to_period_cell_flux,
)
from openmethane_prior.lib.sector.au_sector import AustraliaPriorSector

from .data.vic_oil_gas_fields import vic_oil_gas_data_source
from .safeguard_oil_gas import allocate_safeguard_facility_emissions

logger = logger.get_logger(__name__)

oil_gas_facilities_data_source = DataSource(
    name="oil-gas-facilities",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/oil-and-gas-production-and-transport_emissions-sources.csv",
    parse=parse_csv,
)

def process_emissions(sector: AustraliaPriorSector, sector_config: PriorSectorConfig, prior_ds: xr.Dataset):
    config = sector_config.prior_config

    # prepare a grid to allocate emissions
    domain_grid = config.domain_grid()
    methane = np.zeros(domain_grid.shape)

    safeguard_mechanism_asset = sector_config.data_manager.get_asset(safeguard_mechanism_data_source)
    facility_locations_asset = sector_config.data_manager.get_asset(safeguard_locations_data_source)
    oil_gas_asset = sector_config.data_manager.get_asset(vic_oil_gas_data_source)

    safeguard_facilities, safeguard_locations, safeguard_gridded_ch4 = allocate_safeguard_facility_emissions(
        config=config,
        anzsic_codes=sector.anzsic_codes,
        safeguard_facilities_asset=safeguard_mechanism_asset,
        facility_locations_asset=facility_locations_asset,
        reference_data_asset=oil_gas_asset,
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

    # now read climate_trace facilities emissions for oil and gas
    oil_gas_facilities_asset = sector_config.data_manager.get_asset(oil_gas_facilities_data_source)

    # select gas and year
    oil_gas_ch4 = oil_gas_facilities_asset.data.loc[oil_gas_facilities_asset.data["gas"] == "ch4"]
    oil_gas_ch4.loc[:, "start_time"] = pd.to_datetime(oil_gas_ch4["start_time"])
    target_date = (
        config.start_date
        if config.start_date <= oil_gas_ch4["start_time"].max()
        else oil_gas_ch4["start_time"].max()
    )  # start date or latest date in data
    years = np.array([x.year for x in oil_gas_ch4["start_time"]])
    mask = years == target_date.year
    oil_gas_year = oil_gas_ch4.loc[mask, :]

    # allocate SGM facility emissions across the entire inventory domain, so
    # we can locate facilities which already have emissions allocated and
    # remove them from the secondary data source to prevent doubling up.
    _, _, safeguard_inventory_ch4 = allocate_safeguard_facility_emissions(
        config=config,
        anzsic_codes=sector.anzsic_codes,
        safeguard_facilities_asset=safeguard_mechanism_asset,
        facility_locations_asset=facility_locations_asset,
        reference_data_asset=oil_gas_asset,
        grid=config.inventory_grid(),
    )
    for _, facility in oil_gas_year.iterrows():
        cell_x, cell_y, cell_valid = domain_grid.lonlat_to_cell_index(facility["lon"], facility["lat"])
        if safeguard_inventory_ch4[cell_y, cell_x] > 0:
            # if the cell for this facility has emissions in the SGM, zero
            # it in the secondary data source to prevent double counting
            facility["emissions_quantity"] = 0

    # normalise emissions to match inventory total
    oil_gas_year.loc[:, "emissions_quantity"] *= (
        sector_unallocated_emissions / oil_gas_year["emissions_quantity"].sum()
    )

    # allocate the remaining locations emissions to the grid by allocating
    # the remaining inventory emissions to locations, scaled by their relative
    # fraction of the total emissions
    facilities_gridded = np.zeros(domain_grid.shape)
    for _, facility in oil_gas_year.iterrows():
        cell_x, cell_y, cell_valid = domain_grid.lonlat_to_cell_index(facility["lon"], facility["lat"])
        if cell_valid:
            facilities_gridded[cell_y, cell_x] += facility["emissions_quantity"]

    # convert to kg/m2/s before adding to the result
    methane += kg_to_period_cell_flux(facilities_gridded, config)

    return methane


sector = AustraliaPriorSector(
    name="oil_gas",
    emission_category="anthropogenic",
    unfccc_categories=["1.B.2"], # Fugitive emissions from fuels, Oil and Natural Gas
    anzsic_codes=["07"], # Oil and Gas Extraction
    cf_standard_name="extraction_production_and_transport_of_fuel",
    create_estimate=process_emissions,
)
