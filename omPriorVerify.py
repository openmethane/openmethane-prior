import omInputs
from omInputs import sectoralEmissionsPath
import pandas as pd
import xarray as xr
import numpy as np
import os
from colorama import Fore


# Check ouput sector emissions to make sure they tally up to the input emissions
def verifyEmis():
    domainOutputPath = os.path.join("outputs", f"om-{omInputs.domainFilename}")
    sectorData = pd.read_csv(sectoralEmissionsPath).to_dict(orient="records")[0]

    # Load Livestock inventory and check that it doesn't exceed total agriculture inventory
    with xr.open_dataset(omInputs.livestockDataPath) as lss:
        ls = lss.load()
    lsVal = round(np.sum(ls["CH4_total"].values) / 1000)
    agVal = round(sectorData["agriculture"] * 1000000)
    agDX = agVal - lsVal

    if agDX > 0:
        print(f"{Fore.GREEN}PASSED - Livestock CH4 within bounds of total agriculture CH4: {agDX}")
    else:
        print(f"{Fore.RED}FAILED - Livestock CH4 exceeds bounds of total agriculture CH4: {agDX}")

    # Check each layer in the output sums up to the input
    with xr.open_dataset(domainOutputPath) as dss:
        ds = dss.load()

    for sector in sectorData.keys():
        layerName = f"OCH4_{sector.upper()}"
        sectorVal = round(sectorData[sector] * 1000000)

        if layerName in ds:
            layerVal = round(np.sum(ds[layerName].values))
            if layerVal != sectorVal:
                print(
                    f"{Fore.RED}FAILED - Discrepency of {layerVal - sectorVal}t in {sector} emissions"
                )
            else:
                print(f"{Fore.GREEN}PASSED - {sector} emissions OK")


if __name__ == "__main__":
    verifyEmis()
