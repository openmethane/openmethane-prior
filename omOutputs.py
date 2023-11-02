"""
omOutputs.py

Copyright 2023 The Superpower Institute Ltd
Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

import os
import xarray as xr
import numpy as np
import omInputs 
from omUtils import secsPerYear, getenv

intermediatesPath = getenv("INTERMEDIATES")
outputsPath = getenv("OUTPUTS")
domainFilename = getenv("DOMAIN")

landuseReprojectionPath = os.path.join(intermediatesPath, "land-use.tif")
ntlReprojectionPath = os.path.join(intermediatesPath, "night-time-lights.tif")
domainOutputPath = os.path.join(outputsPath, f"out-{domainFilename}")
geoJSONOutputPath = os.path.join(outputsPath, "grid-cells.json")
ch4JSONOutputPath = os.path.join(outputsPath, "methane.json")

coordNames = ['TSTEP', 'ROW', 'COL']

# Convert a gridded emission in kgs/cell/year to kgs/m2/s
def convertToTimescale(emission):
    di = omInputs.domainXr
    domainCellAreaM2 = di.DX * di.DY
    return emission / domainCellAreaM2 / secsPerYear

def writeLayer(layerName, layerData, directSet = False):
    print(f"Writing emissions data for {layerName}")
    
    datapath = domainOutputPath if os.path.exists(domainOutputPath) else omInputs.domainPath
    with xr.open_dataset(datapath) as dss:
        ds = dss.load()
    # if this is a xr dataArray just include it
    if directSet:
        ds[layerName] = layerData
    else:
        nDims = len(layerData.shape)
        ds[layerName] = (coordNames[-nDims:], layerData)
    ds.to_netcdf(domainOutputPath) 

def sumLayers():
    layers = omInputs.omLayers

    if os.path.exists(domainOutputPath):
        with xr.open_dataset(domainOutputPath) as dss:
            ds = dss.load()

        # now check to find largest shape because we'll broadcast everything else to that
        summedSize = 0
        for layer in layers:
            layerName = f"OCH4_{layer.upper()}"
            
            if layerName in ds:
                if ds[ layerName].size > summedSize:
                    summedShape = ds[layerName].shape
                    summedSize = ds[ layerName].size

        summed = None
        for layer in layers:
            layerName = f"OCH4_{layer.upper()}"
            
            if layerName in ds:
                if summed is None:
                    summed = np.zeros( summedShape)
                summed += ds[layerName].values # it will broadcast time dimensions of 1 correctly
        
        if summed is not None:
             nDims = len(summed.shape)
             ds["OCH4_TOTAL"] = (['Time']+list( coordNames[-2:]), summed)
             ds.to_netcdf(domainOutputPath)

