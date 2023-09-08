import numpy as np
from omInputs import fugitivesPath, sectoralEmissionsPath, domainXr as ds, domainProj
from omOutputs import writeLayer, convertToTimescale
import pandas as pd
import math

def processEmissions():
    print("processEmissions for fugitives")
    fugitiveEmis = pd.read_csv(sectoralEmissionsPath).to_dict(orient='records')[0]["fugitive"] * 1000000
    fugitiveFacilities = pd.read_csv(fugitivesPath, header=0).to_dict(orient='records')
    fugitiveEmisPerFacility = fugitiveEmis / len(fugitiveFacilities)
    landmask = ds["LANDMASK"][:]

    _, lmy, lmx = landmask.shape
    ww = ds.DX * lmx
    hh = ds.DY * lmy

    methane = np.zeros(landmask.shape)

    for facility in fugitiveFacilities:
        x, y = domainProj(facility["lng"], facility["lat"])
        ix = math.floor((x + ww / 2) / ds.DX)
        iy = math.floor((y + hh / 2) / ds.DY)
        methane[0][iy][ix] += fugitiveEmisPerFacility

    writeLayer("OCH4_FUGITIVE", convertToTimescale(methane))

if __name__ == '__main__':
    processEmissions()
