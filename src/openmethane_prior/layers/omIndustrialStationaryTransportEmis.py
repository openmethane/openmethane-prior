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

"""
Processing industrual stationary transport emissions
"""

import numpy as np
import xarray as xr
import rioxarray as rxr
from ..omInputs import sectoralEmissionsPath, auShapefilePath, domainXr as ds, domainProj
from ..omOutputs import ntlReprojectionPath, writeLayer, convertToTimescale, sumLayers
import pandas as pd
import geopandas

def processEmissions():
    print("processEmissions for Industrial, Stationary and Transport")

    sectorsUsed = ["industrial", "stationary", "transport"]
    _ntlData = rxr.open_rasterio(ntlReprojectionPath, masked=True)

    print("Clipping night-time lights data to Australian land border")
    ausf = geopandas.read_file(auShapefilePath)
    ausf_rp = ausf.to_crs(domainProj.crs)
    ntlData = _ntlData.rio.clip(ausf_rp.geometry.values, ausf_rp.crs)

    # Add together the intensity of the 3 channels for a total intensity per pixel
    numNtltData = np.nan_to_num(ntlData)
    ntlt = np.nan_to_num(numNtltData[0] + numNtltData[1] + numNtltData[2])

    # Sum all pixel intensities
    ntltTotal = np.sum(ntlt)

    # Divide each pixel intensity by the total to get a scaled intensity per pixel
    ntltScalar = ntlt / ntltTotal

    sectorData = pd.read_csv(sectoralEmissionsPath).to_dict(orient='records')[0]
    ntlIndustrial = ntltScalar * (sectorData["industrial"]  * 1e9)
    ntlStationary = ntltScalar * (sectorData["stationary"] * 1e9)
    ntlTransport = ntltScalar * (sectorData["transport"]  * 1e9)

    # Load domain
    landmask = ds["LANDMASK"][:]

    _, lmy, lmx = landmask.shape
    ww = ds.DX * lmx
    hh = ds.DY * lmy

    print("Mapping night-time lights grid to domain grid")
    findGrid = lambda data, totalSize, gridSize: np.floor((data + totalSize / 2) / gridSize)
    xDomain = xr.apply_ufunc(findGrid, ntlData.x, ww, ds.DX).values.astype(int)
    yDomain = xr.apply_ufunc(findGrid, ntlData.y, hh, ds.DY).values.astype(int)

    # xDomain = np.floor((ntlData.x + ww / 2) / ds.DX).astype(int)
    # yDomain = np.floor((ntlData.y + hh / 2) / ds.DY).astype(int)

    methane = {}
    for sector in sectorsUsed:
        methane[sector] = np.zeros(ds["LANDMASK"].shape)

    litPixels = np.argwhere(ntlt > 0)
    ignored = 0

    for y, x in litPixels:
        try:
            methane["industrial"][0][yDomain[y]][xDomain[x]] += ntlIndustrial[y][x]
            methane["stationary"][0][yDomain[y]][xDomain[x]] += ntlStationary[y][x]
            methane["transport"][0][yDomain[y]][xDomain[x]] += ntlTransport[y][x]
        except Exception as e:
            # print(e)
            ignored += 1

    print(f"{ignored} lit pixels were ignored")

    for sector in sectorsUsed:
        writeLayer(f"OCH4_{sector.upper()}", convertToTimescale(methane[sector]))

if __name__ == '__main__':
    # reprojectRasterInputs()
    processEmissions()
    sumLayers()