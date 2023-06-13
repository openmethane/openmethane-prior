import numpy as np
import netCDF4 as nc
import xarray as xr
import rioxarray as rxr
from omInputs import domainPath, sectoralEmissionsPath, auShapefilePath
from omOutputs import ntlReprojectionPath, writeLayer
import pandas as pd
import geopandas
import pyproj

def processEmissions():
    print("processEmissions for Industrial, Staionary and Transport")

    _ntlData = rxr.open_rasterio(ntlReprojectionPath, masked=True)

    ds = xr.open_dataset(domainPath)
    domainProj = pyproj.Proj(proj='lcc', lat_1=ds.TRUELAT1, lat_2=ds.TRUELAT2, lat_0=ds.MOAD_CEN_LAT, lon_0=ds.STAND_LON, a=6370000, b=6370000)

    print("Clipping night-time lights data to Australian land border")
    ausf = geopandas.read_file(auShapefilePath)
    ausf_rp = ausf.to_crs(domainProj.crs)
    ntlData = _ntlData.rio.clip(ausf_rp.geometry.values, ausf_rp.crs)

    ntlt = ntlData[0] + ntlData[1] + ntlData[2]
    ntltScalar = ntlt / np.sum(ntlt)

    sectorData = pd.read_csv(sectoralEmissionsPath).to_dict(orient='records')[0]

    ntlIndustrial = ntltScalar * sectorData["industrial"]
    ntlStationary = ntltScalar * sectorData["stationary"]
    ntlTransport = ntltScalar * sectorData["transport"]

    # Load domain
    ds = nc.Dataset(domainPath)
    landmask = ds["LANDMASK"][:]

    _, lmy, lmx = landmask.shape
    ww = ds.DX * lmx
    hh = ds.DY * lmy

    print("Mapping night-time lights grid to domain grid")
    findGrid = lambda data, totalSize, gridSize: np.floor((data + totalSize / 2) / gridSize)
    xDomain = xr.apply_ufunc(findGrid, ntlData.x, ww, ds.DX).values.astype(int)
    yDomain = xr.apply_ufunc(findGrid, ntlData.y, hh, ds.DY).values.astype(int)

    methane = {}
    for sector in ["industrial", "stationary", "transport"]:
        methane[sector] = np.zeros(ds["LANDMASK"].shape)

    litPixels = np.argwhere(ntlt.values > 0)
    ignored = 0
    for y, x in litPixels:
        try:
            methane["industrial"][0][yDomain[y]][xDomain[x]] += ntlIndustrial[y][x]
            methane["stationary"][0][yDomain[y]][xDomain[x]] += ntlStationary[y][x]
            methane["transport"][0][yDomain[y]][xDomain[x]] += ntlTransport[y][x]
        except:
            # print(f"ignoring out of range pixel {yDomain[y]}, {xDomain[x]}")
            ignored += 1

    writeLayer(f"OCH4_{'industrial'.upper()}", methane["industrial"])
    writeLayer(f"OCH4_{'stationary'.upper()}", methane["stationary"])
    writeLayer(f"OCH4_{'transport'.upper()}", methane["transport"])