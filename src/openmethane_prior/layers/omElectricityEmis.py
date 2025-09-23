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

"""Process emissions from the electricity sector"""

import numpy as np
import pandas as pd
import xarray as xr

from openmethane_prior.config import PriorConfig, load_config_from_env, parse_cli_to_env
from openmethane_prior.data_manager.manager import DataManager
from openmethane_prior.outputs import (
    add_ch4_total,
    add_sector,
    create_output_dataset,
    write_output_dataset,
)
import openmethane_prior.logger as logger
from openmethane_prior.inventory.inventory import load_inventory, get_sector_emissions_by_code
from openmethane_prior.sector.config import PriorSectorConfig
from openmethane_prior.sector.sector import SectorMeta
from openmethane_prior.units import kg_to_period_cell_flux

logger = logger.get_logger(__name__)

sector_meta = SectorMeta(
    name="electricity",
    emission_category="anthropogenic",
    unfccc_categories=["1.A.1.a"], # Public electricity and heat production
    cf_standard_name="energy_production_and_distribution",
)

def processEmissions(sector_config: PriorSectorConfig, prior_ds: xr.Dataset):
    """
    Process emissions from the electricity sector, adding them to the prior
    dataset.
    """
    logger.info("processEmissions for electricity")
    config = sector_config.prior_config

    # read the total emissions over the sector (in kg)
    emissions_inventory = load_inventory(config)
    sector_total_emissions = get_sector_emissions_by_code(
        emissions_inventory=emissions_inventory,
        start_date=config.start_date,
        end_date=config.end_date,
        category_codes=sector_meta.unfccc_categories,
    )

    electricityFacilities = pd.read_csv(
        config.as_input_file(config.layer_inputs.electricity_path), header=0
    ).to_dict(orient="records")

    domain_grid = config.domain_grid()

    totalCapacity = sum(item["capacity"] for item in electricityFacilities)

    methane = np.zeros(domain_grid.shape)

    for facility in electricityFacilities:
        cell_x, cell_y, cell_valid = domain_grid.lonlat_to_cell_index(facility["lng"], facility["lat"])

        if cell_valid:
            methane[cell_y, cell_x] += (facility["capacity"] / totalCapacity) * sector_total_emissions

    add_sector(
        prior_ds=prior_ds,
        sector_data=kg_to_period_cell_flux(methane, config),
        sector_meta=sector_meta,
    )


if __name__ == "__main__":
    parse_cli_to_env()
    config = load_config_from_env()
    data_manager = DataManager(data_path=config.input_path)
    sector_config = PriorSectorConfig(prior_config=config, data_manager=data_manager)

    ds = create_output_dataset(config)
    processEmissions(sector_config, ds)
    add_ch4_total(ds)
    write_output_dataset(config, ds)
