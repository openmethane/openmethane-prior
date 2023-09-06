import os
import xarray as xr
import pandas as pd
import numpy as np
import omInputs 

landuseReprojectionPath = os.path.join("outputs", "land-use.tif")
ntlReprojectionPath = os.path.join("outputs", "night-time-lights.tif")
domainOutputPath = os.path.join("outputs", f"om-{omInputs.domainFilename}")
geoJSONOutputPath = os.path.join("outputs", "cells.json")
ch4JSONOutputPath = os.path.join("outputs", "methane.json")

def writeLayer(layerName, layerData):
    print(f"Writing emissions data for {layerName}")
    datapath = domainOutputPath if os.path.exists(domainOutputPath) else omInputs.domainPath
    with xr.open_dataset(datapath) as dss:
            ds = dss.load()

    ds[layerName] = (('Time', 'south_north', 'west_east'), layerData)
    ds.to_netcdf(domainOutputPath)

def sumLayers():
    sectors = pd.read_csv(omInputs.sectoralEmissionsPath, index_col=0, nrows=0).columns.tolist()
    if os.path.exists(domainOutputPath):
        with xr.open_dataset(domainOutputPath) as dss:
            ds = dss.load()

        summed = None
        for sector in sectors:
            layerName = f"OCH4_{sector.upper()}"
            if layerName in ds:
                if summed is None:
                    summed = np.zeros(ds[layerName].shape)
                summed = summed + ds[layerName].values
        
        if summed is not None:
             ds["OCH4_TOTAL"] = (('Time', 'south_north', 'west_east'), summed)
             ds.to_netcdf(domainOutputPath)

