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

from openmethane_prior.data_sources.climate_trace import filter_emissions_sources
from openmethane_prior.data_sources.inventory import get_sector_emissions_by_code, inventory_data_source
from openmethane_prior.lib import (
    kg_to_period_cell_flux,
    logger,
    PriorSectorConfig,
)
from openmethane_prior.lib.sector.au_sector import AustraliaPriorSector

from .data import (
    ct_wastewaster_domestic_data_source,
    ct_wastewaster_industrial_data_source,
    ct_solid_waste_data_source,
)

logger = logger.get_logger(__name__)


def process_emissions(
        sector: AustraliaPriorSector,
        sector_config: PriorSectorConfig,
        prior_ds: xr.Dataset,
):
    config = sector_config.prior_config
    domain_grid = config.domain_grid()

    # load the national inventory data, ready to calculate sectoral totals
    emissions_inventory = sector_config.data_manager.get_asset(inventory_data_source).data
    sector_total_emissions = get_sector_emissions_by_code(
        emissions_inventory=emissions_inventory,
        start_date=config.start_date,
        end_date=config.end_date,
        category_codes=sector.unfccc_categories,
    )

    # read all emissions sources corresponding to the waste sector
    emissions_sources = pd.concat([
        sector_config.data_manager.get_asset(ct_wastewaster_domestic_data_source).data,
        sector_config.data_manager.get_asset(ct_wastewaster_industrial_data_source).data,
        sector_config.data_manager.get_asset(ct_solid_waste_data_source).data,
    ])

    # select the emissions source data from the requested period
    period_emissions_sources = filter_emissions_sources(
        emissions_sources,
        config.start_date,
        config.end_date,
    )

    # scale site emissions so the aggregate matches the inventory total
    period_emissions_sources.loc[:, "emissions_quantity"] *= (
        sector_total_emissions / period_emissions_sources["emissions_quantity"].sum()
    )

    sector_gridded = np.zeros(domain_grid.shape)
    for _, facility in period_emissions_sources.iterrows():
        cell_x, cell_y, cell_valid = domain_grid.lonlat_to_cell_index(facility["lon"], facility["lat"])

        if cell_valid:
            sector_gridded[cell_y, cell_x] += facility["emissions_quantity"]

    return kg_to_period_cell_flux(sector_gridded, config)


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
