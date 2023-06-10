import numpy as np
import xarray as xr
import pyproj
from omInputs import fugitivesPath, sectoralEmissionsPath, domainPath
from omOutputs import writeLayer, domainOutputPath
import pandas as pd
import math

def processEmissions():
    fugitiveEmis = pd.read_csv(sectoralEmissionsPath).to_dict(orient='records')[0]["fugitive"]
    fugitiveFacilities = pd.read_csv(fugitivesPath, header=0).to_dict(orient='records')
    fugitiveEmisPerFacility = fugitiveEmis / len(fugitiveFacilities)

    ds = xr.open_dataset(domainPath)
    domainProj = pyproj.Proj(proj='lcc', lat_1=ds.TRUELAT1, lat_2=ds.TRUELAT2, lat_0=ds.MOAD_CEN_LAT, lon_0=ds.STAND_LON, a=6370000, b=6370000)

    landmask = ds["LANDMASK"][:]

    _, lmy, lmx = landmask.shape
    ww = ds.DX * lmx
    hh = ds.DY * lmy

    methane = np.zeros(ds["LANDMASK"].shape)

    for facility in fugitiveFacilities:
        x, y = domainProj(facility["lng"], facility["lat"])
        ix = math.floor((x + ww / 2) / ds.DX)
        iy = math.floor((y + hh / 2) / ds.DY)
        methane[0][iy][ix] += fugitiveEmisPerFacility

    layerName = f"OCH4_{'fugitive'.upper()}"
    writeLayer(layerName, methane)