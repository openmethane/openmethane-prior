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

"""Process fugitive Methane emissions"""

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
    name="fugitive",
    emission_category="anthropogenic",
    unfccc_categories=["1.B"], # Fugitive emissions from fuels
    cf_standard_name="extraction_production_and_transport_of_fuel",
)

def processEmissions(sector_config: PriorSectorConfig, prior_ds: xr.Dataset):
    """
    Process the fugitive methane emissions

    Adds the ch4_fugitive layer to the output
    """
    logger.info("processEmissions for fugitives")
    config = sector_config.prior_config

    # read the total emissions over the sector (in kg)
    emissions_inventory = load_inventory(config)
    sector_total_emissions = get_sector_emissions_by_code(
        emissions_inventory=emissions_inventory,
        start_date=config.start_date,
        end_date=config.end_date,
        category_codes=sector_meta.unfccc_categories,
    )

    # now read climate_trace facilities emissions for coal, oil and gas
    coalFacilities = pd.read_csv(config.as_input_file(config.layer_inputs.coal_path))
    oilGasFacilities = pd.read_csv(config.as_input_file(config.layer_inputs.oil_gas_path))
    fugitiveFacilities = pd.concat((coalFacilities, oilGasFacilities))

    # select gas and year
    fugitiveCH4 = fugitiveFacilities.loc[fugitiveFacilities["gas"] == "ch4"]
    fugitiveCH4.loc[:, "start_time"] = pd.to_datetime(fugitiveCH4["start_time"])
    targetDate = (
        config.start_date
        if config.start_date <= fugitiveCH4["start_time"].max()
        else fugitiveCH4["start_time"].max()
    )  # start date or latest date in data
    years = np.array([x.year for x in fugitiveCH4["start_time"]])
    mask = years == targetDate.year
    fugitiveYear = fugitiveCH4.loc[mask, :]
    # normalise emissions to match inventory total
    fugitiveYear.loc[:, "emissions_quantity"] *= (
        sector_total_emissions / fugitiveYear["emissions_quantity"].sum()
    )

    domain_grid = config.domain_grid()

    methane = np.zeros(domain_grid.shape)

    for _, facility in fugitiveYear.iterrows():
        cell_x, cell_y, cell_valid = domain_grid.lonlat_to_cell_index(facility["lon"], facility["lat"])

        if cell_valid:
            methane[cell_y, cell_x] += facility["emissions_quantity"]

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
