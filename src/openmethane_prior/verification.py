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

"""Utilities for verifying the generated output file"""

import numpy as np
import pandas as pd
import xarray as xr
from colorama import Fore

from openmethane_prior.config import PriorConfig, load_config_from_env
from openmethane_prior.outputs import SECTOR_PREFIX
from openmethane_prior.utils import SECS_PER_YEAR
import openmethane_prior.logger as logger

logger = logger.get_logger(__name__)

MAX_ABS_DIFF = 0.1


def verify_emis(config: PriorConfig, prior_ds: xr.Dataset, atol: float = MAX_ABS_DIFF):
    """Check output sector emissions to make sure they tally up to the input emissions"""
    sector_data = pd.read_csv(
        config.as_input_file(config.layer_inputs.sectoral_emissions_path)
    ).to_dict(orient="records")[0]

    passed = []
    failed = []

    # Load Livestock inventory and check that it doesn't exceed total agriculture inventory
    with xr.open_dataset(config.as_input_file(config.layer_inputs.livestock_path)) as lss:
        ls = lss.load()
    livestock_inventory_total = round(np.sum(ls["CH4_total"].values))
    agriculture_inventory_total = round(sector_data["agriculture"] * 1e9)
    agriculture_remaining = (agriculture_inventory_total - livestock_inventory_total) / 1e9

    if agriculture_remaining > 0:
        passed.append(f"Livestock CH4 within bounds of total agriculture CH4: {agriculture_remaining}")
    else:
        failed.append(f"Livestock CH4 exceeds bounds of total agriculture CH4: {agriculture_remaining}")

    # Check each layer in the output sums up to the input
    m2s_to_kg = config.domain_grid().cell_area * SECS_PER_YEAR
    for sector in sector_data.keys():
        layerName = f"{SECTOR_PREFIX}_{sector}"
        sectorVal = float(sector_data[sector]) * 1e9

        if layerName in prior_ds:
            layerVal = np.sum(prior_ds[layerName][0].values * m2s_to_kg)

            if sector == "agriculture":
                layerVal += np.sum(prior_ds[f"{SECTOR_PREFIX}_livestock"][0].values * m2s_to_kg)

            diff = round(layerVal - sectorVal)
            pct_diff = diff / sectorVal * 100

            if abs(pct_diff) > atol:
                failed.append(f"Discrepancy of {pct_diff}% in {sector} emissions")
            else:
                passed.append(f"{sector} emissions OK, discrepancy is {abs(pct_diff)}% of total")

    for passed_msg in passed:
        logger.debug(f"{Fore.GREEN}PASSED{Fore.RESET} - {passed_msg}")
    for failed_msg in failed:
        logger.warning(f"{Fore.RED}FAILED{Fore.RESET} - {failed_msg}")

if __name__ == "__main__":
    config = load_config_from_env()
    verify_emis(config=config, prior_ds=xr.open_dataset(config.output_file))
