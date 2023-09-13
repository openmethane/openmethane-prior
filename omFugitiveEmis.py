"""
omFugitiveEmis.py

Copyright 2023 The Superpower Institute Ltd
Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

import numpy as np
from omInputs import fugitivesPath, sectoralEmissionsPath, domainXr as ds, domainProj
from omOutputs import writeLayer, convertToTimescale, sumLayers
import pandas as pd
import math

def processEmissions():
    print("processEmissions for fugitives")
    fugitiveEmis = pd.read_csv(sectoralEmissionsPath).to_dict(orient='records')[0]["fugitive"] * 1e9
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
    sumLayers()
