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
    sectorData = pd.read_csv(sectoralEmissionsPath).to_dict(orient='records')[0]

    with xr.open_dataset(domainOutputPath) as dss:
        ds = dss.load()

    for sector in sectorData.keys():
        layerName = f"OCH4_{sector.upper()}"
        sectorVal = round(sectorData[sector] * 1000000)

        if layerName in ds:
            layerVal = round(np.sum(ds[layerName].values))
            if layerVal != sectorVal:
                print(f"{Fore.RED}FAILED - Discrepency of {layerVal - sectorVal}t in {sector} emissions")
            else:
                print(f"{Fore.GREEN}PASSED - {sector} emissions OK")

if __name__ == '__main__':
    verifyEmis()