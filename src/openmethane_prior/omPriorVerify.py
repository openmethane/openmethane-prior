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
from openmethane_prior.omUtils import SECS_PER_YEAR

MAX_ABS_DIFF = 0.1


def verify_emis(config: PriorConfig, atol: float = MAX_ABS_DIFF):
    """Check output sector emissions to make sure they tally up to the input emissions"""
    sector_data = pd.read_csv(
        config.as_input_file(config.layer_inputs.sectoral_emissions_path)
    ).to_dict(orient="records")[0]

    # Load Livestock inventory and check that it doesn't exceed total agriculture inventory
    with xr.open_dataset(config.as_input_file(config.layer_inputs.livestock_path)) as lss:
        ls = lss.load()
    lsVal = round(np.sum(ls["CH4_total"].values))
    agVal = round(sector_data["agriculture"] * 1e9)
    agDX = agVal - lsVal

    if agDX > 0:
        print(
            f"{Fore.GREEN}PASSED - "
            f"Livestock CH4 within bounds of total agriculture CH4: {agDX / 1e9}"
        )
    else:
        print(
            f"{Fore.RED}FAILED - "
            f"Livestock CH4 exceeds bounds of total agriculture CH4: {agDX / 1e9}"
        )

    # Check each layer in the output sums up to the input
    with xr.open_dataset(config.output_domain_file) as dss:
        ds = dss.load()

    modelAreaM2 = ds.DX * ds.DY
    for sector in sector_data.keys():
        layerName = f"OCH4_{sector.upper()}"
        sectorVal = float(sector_data[sector]) * 1e9

        if layerName in ds:
            layerVal = np.sum(ds[layerName][0].values * modelAreaM2 * SECS_PER_YEAR)

            if sector == "agriculture":
                layerVal += np.sum(ds["OCH4_LIVESTOCK"][0].values * modelAreaM2 * SECS_PER_YEAR)

            diff = round(layerVal - sectorVal)
            pct_diff = diff / sectorVal * 100

            if abs(pct_diff) > atol:
                print(f"{Fore.RED}FAILED - " f"Discrepancy of {pct_diff}% in {sector} emissions")
            else:
                print(
                    f"{Fore.GREEN}PASSED - "
                    f"{sector} emissions OK, discrepancy is {abs(pct_diff)}% of total"
                )


if __name__ == "__main__":
    config = load_config_from_env()
    verify_emis(config)
