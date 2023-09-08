import numpy as np
import xarray as xr
import pyproj
from omInputs import fugitivesPath, sectoralEmissionsPath, domainXr
from omOutputs import writeLayer, domainOutputPath
import pandas as pd
import math

def processEmissions():
    print("processEmissions for fugitives")
    fugitiveEmis = pd.read_csv(sectoralEmissionsPath).to_dict(orient='records')[0]["fugitive"] * 1000000
    fugitiveFacilities = pd.read_csv(fugitivesPath, header=0).to_dict(orient='records')
    fugitiveEmisPerFacility = fugitiveEmis / len(fugitiveFacilities)

    domainProj = pyproj.Proj(proj='lcc', lat_1=domainXr.TRUELAT1, lat_2=domainXr.TRUELAT2, lat_0=domainXr.MOAD_CEN_LAT, lon_0=domainXr.STAND_LON, a=6370000, b=6370000)

    landmask = domainXr["LANDMASK"].values.squeeze()

    lmy, lmx = landmask.shape
    ww = domainXr.DX * lmx
    hh = domainXr.DY * lmy

    methane = np.zeros(landmask.shape)

    for facility in fugitiveFacilities:
        x, y = domainProj(facility["lng"], facility["lat"])
        ix = math.floor((x + ww / 2) / domainXr.DX)
        iy = math.floor((y + hh / 2) / domainXr.DY)
        methane[iy][ix] += fugitiveEmisPerFacility

    writeLayer("OCH4_FUGITIVE", methane)

if __name__ == '__main__':
    processEmissions()
