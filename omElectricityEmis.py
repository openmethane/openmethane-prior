import numpy as np
from omInputs import electricityPath, sectoralEmissionsPath, domainInfo as ds, domainProj
from omOutputs import writeLayer, convertToTimescale
import pandas as pd
import math

def processEmissions():
    print("processEmissions for Electricity")

    electricityEmis = pd.read_csv(sectoralEmissionsPath).to_dict(orient='records')[0]["electricity"] * 1e9
    electricityFacilities = pd.read_csv(electricityPath, header=0).to_dict(orient='records')
    electricityEmisPerFacility = electricityEmis / len(electricityFacilities)
    landmask = ds["LANDMASK"][:]

    _, lmy, lmx = landmask.shape
    ww = ds.DX * lmx
    hh = ds.DY * lmy

    methane = np.zeros(ds["LANDMASK"].shape)

    for facility in electricityFacilities:
        x, y = domainProj(facility["lng"], facility["lat"])
        ix = math.floor((x + ww / 2) / ds.DX)
        iy = math.floor((y + hh / 2) / ds.DY)
        methane[0][iy][ix] += electricityEmisPerFacility

    writeLayer("OCH4_ELECTRICITY", convertToTimescale(methane))

if __name__ == '__main__':
    processEmissions()