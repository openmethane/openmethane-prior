import numpy as np
import xarray as xr
import rioxarray as rxr
from omInputs import sectoralEmissionsPath, auShapefilePath, domainInfo as ds, domainProj
from omOutputs import ntlReprojectionPath, writeLayer, convertToTimescale
import pandas as pd
import geopandas

def processEmissions():
    print("processEmissions for Industrial, Staionary and Transport")

    sectorsUsed = ["industrial", "stationary", "transport"]
    _ntlData = rxr.open_rasterio(ntlReprojectionPath, masked=True)

    print("Clipping night-time lights data to Australian land border")
    ausf = geopandas.read_file(auShapefilePath)
    ausf_rp = ausf.to_crs(domainProj.crs)
    ntlData = _ntlData.rio.clip(ausf_rp.geometry.values, ausf_rp.crs)

    ntlt = ntlData[0] + ntlData[1] + ntlData[2]
    ntltScalar = ntlt / np.sum(ntlt)

    sectorData = pd.read_csv(sectoralEmissionsPath).to_dict(orient='records')[0]

    ntlIndustrial = ntltScalar * (sectorData["industrial"]  * 1000000)
    ntlStationary = ntltScalar * (sectorData["stationary"] * 1000000)
    ntlTransport = ntltScalar * (sectorData["transport"]  * 1000000)

    # Load domain
    landmask = ds["LANDMASK"][:]

    _, lmy, lmx = landmask.shape
    ww = ds.DX * lmx
    hh = ds.DY * lmy

    print("Mapping night-time lights grid to domain grid")
    findGrid = lambda data, totalSize, gridSize: np.floor((data + totalSize / 2) / gridSize)
    xDomain = xr.apply_ufunc(findGrid, ntlData.x, ww, ds.DX).values.astype(int)
    yDomain = xr.apply_ufunc(findGrid, ntlData.y, hh, ds.DY).values.astype(int)

    methane = {}
    for sector in sectorsUsed:
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

    for sector in sectorsUsed:
        writeLayer(f"OCH4_{sector.upper()}",convertToTimescale(methane[sector]))

if __name__ == '__main__':
    processEmissions()