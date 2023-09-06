import numpy as np
import xarray as xr
import pyproj
from omInputs import electricityPath, sectoralEmissionsPath, domainPath
from omOutputs import writeLayer
import pandas as pd
import math

def processEmissions():
    print("processEmissions for Electricity")

    electricityEmis = pd.read_csv(sectoralEmissionsPath).to_dict(orient='records')[0]["electricity"] * 1000000
    electricityFacilities = pd.read_csv(electricityPath, header=0).to_dict(orient='records')
    electricityEmisPerFacility = electricityEmis / len(electricityFacilities)

    ds = xr.open_dataset(domainPath)
    domainProj = pyproj.Proj(proj='lcc', lat_1=ds.TRUELAT1, lat_2=ds.TRUELAT2, lat_0=ds.MOAD_CEN_LAT, lon_0=ds.STAND_LON, a=6370000, b=6370000)

    landmask = ds["LANDMASK"][:].squeeze()

    lmy, lmx = landmask.shape
    ww = ds.DX * lmx
    hh = ds.DY * lmy

    methane = np.zeros((1,)+landmask.shape)

    for facility in electricityFacilities:
        x, y = domainProj(facility["lng"], facility["lat"])
        ix = math.floor((x + ww / 2) / ds.DX)
        iy = math.floor((y + hh / 2) / ds.DY)
        methane[0][iy][ix] += electricityEmisPerFacility

    writeLayer("OCH4_ELECTRICITY", methane)

if __name__ == '__main__':
    processEmissions()
