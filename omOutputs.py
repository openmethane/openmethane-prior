import os
import xarray as xr
import numpy as np
import omInputs 
from utils import secsPerYear

landuseReprojectionPath = os.path.join("outputs", "land-use.tif")
ntlReprojectionPath = os.path.join("outputs", "night-time-lights.tif")
domainOutputPath = os.path.join("outputs", f"om-{omInputs.domainFilename}")
geoJSONOutputPath = os.path.join("outputs", "cells.json")
ch4JSONOutputPath = os.path.join("outputs", "methane.json")

# Convert a gridded emission in kgs/cell/year to kgs/m2/s
def convertToTimescale(emission):
    di = omInputs.domainXr
    domainCellAreaM2 = di.DX * di.DY
    return emission * domainCellAreaM2 / secsPerYear

def writeLayer(layerName, layerData):
    print(f"Writing emissions data for {layerName}")
    datapath = domainOutputPath if os.path.exists(domainOutputPath) else omInputs.domainPath
    with xr.open_dataset(datapath) as dss:
        ds = dss.load()
    # if this is a xr dataArray just include it
    if isinstance( layerData, xr.DataArray):
        ds[layerName] =  layerData
    else:
        ds[layerName] = (('Time', 'south_north', 'west_east'), layerData)
    ds.to_netcdf(domainOutputPath, group='emissions')

def sumLayers():
    layers = omInputs.omLayers

    if os.path.exists(domainOutputPath):
        with xr.open_dataset(domainOutputPath) as dss:
            ds = dss.load()

        summed = None
        for layer in layers:
            layerName = f"OCH4_{layer.upper()}"
            
            if layerName in ds:
                if summed is None:
                    summed = np.zeros(ds[layerName].shape)
                summed = summed + ds[layerName].values
        
        if summed is not None:
             ds["OCH4_TOTAL"] = (('Time', 'south_north', 'west_east'), summed)
             ds.to_netcdf(domainOutputPath)

