import numpy as np
import xarray as xr
import pyproj
from omInputs import electricityPath, sectoralEmissionsPath, domainXr
from omOutputs import writeLayer
import pandas as pd
import math

def processEmissions():
    print("processEmissions for Electricity")

    electricityEmis = pd.read_csv(sectoralEmissionsPath).to_dict(orient='records')[0]["electricity"] * 1000000
    electricityFacilities = pd.read_csv(electricityPath, header=0).to_dict(orient='records')
    electricityEmisPerFacility = electricityEmis / len(electricityFacilities)

    domainProj = pyproj.Proj(proj='lcc', lat_1=domainXr.TRUELAT1, lat_2=domainXr.TRUELAT2, lat_0=domainXr.MOAD_CEN_LAT, lon_0=domainXr.STAND_LON, a=6370000, b=6370000)

    landmask = domainXr["LANDMASK"][:].squeeze()

    lmy, lmx = landmask.shape
    ww = domainXr.DX * lmx
    hh = domainXr.DY * lmy

    methane = np.zeros((1,)+landmask.shape)

    for facility in electricityFacilities:
        x, y = domainProj(facility["lng"], facility["lat"])
        ix = math.floor((x + ww / 2) / domainXr.DX)
        iy = math.floor((y + hh / 2) / domainXr.DY)
        methane[0][iy][ix] += electricityEmisPerFacility

    writeLayer("OCH4_ELECTRICITY", methane)

if __name__ == '__main__':
    processEmissions()
