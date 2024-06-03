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

"""Utilities for verifying the generated output file
"""

import numpy as np
import pandas as pd
import xarray as xr
from colorama import Fore

from openmethane_prior.omInputs import livestockDataPath, sectoralEmissionsPath
from openmethane_prior.omOutputs import domainOutputPath
from openmethane_prior.omUtils import secsPerYear


# Check ouput sector emissions to make sure they tally up to the input emissions
def verifyEmis():
    sectorData = pd.read_csv(sectoralEmissionsPath).to_dict(orient="records")[0]

    # Load Livestock inventory and check that it doesn't exceed total agriculture inventory
    with xr.open_dataset(livestockDataPath) as lss:
        ls = lss.load()
    lsVal = round(np.sum(ls["CH4_total"].values))
    agVal = round(sectorData["agriculture"] * 1e9)
    agDX = agVal - lsVal

    if agDX > 0:
        print(
            f"{Fore.GREEN}PASSED - Livestock CH4 within bounds of total agriculture CH4: {agDX / 1e9}"
        )
    else:
        print(
            f"{Fore.RED}FAILED - Livestock CH4 exceeds bounds of total agriculture CH4: {agDX / 1e9}"
        )

    # Check each layer in the output sums up to the input
    with xr.open_dataset(domainOutputPath) as dss:
        ds = dss.load()

    modelAreaM2 = ds.DX * ds.DY
    for sector in sectorData.keys():
        layerName = f"OCH4_{sector.upper()}"
        sectorVal = float(sectorData[sector]) * 1e9

        if layerName in ds:
            layerVal = np.sum(ds[layerName][0].values * modelAreaM2 * secsPerYear)

            if sector == "agriculture":
                layerVal += np.sum(ds["OCH4_LIVESTOCK"][0].values * modelAreaM2 * secsPerYear)

            diff = round(layerVal - sectorVal)
            perectenageDifference = diff / sectorVal * 100

            if abs(perectenageDifference) > 0.1:
                print(
                    f"{Fore.RED}FAILED - Discrepency of {perectenageDifference}% in {sector} emissions"
                )
            else:
                print(
                    f"{Fore.GREEN}PASSED - {sector} emissions OK, discrepancy is {abs(perectenageDifference)}% of total"
                )


if __name__ == "__main__":
    verifyEmis()
