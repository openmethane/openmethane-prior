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

"""Process emissions from the electricity sector"""

import math

import numpy as np
import pandas as pd

from openmethane_prior.omInputs import (
    domainProj,
    electricityPath,
    sectoralEmissionsPath,
)
from openmethane_prior.omInputs import (
    domainXr as ds,
)
from openmethane_prior.omOutputs import convert_to_timescale, sumLayers, write_layer


def processEmissions():
    """
    Process emissions from the electricity sector

    Adds `OCH4_ELECTRICITY` layer to the output file
    """
    print("processEmissions for Electricity")

    electricityEmis = (
        pd.read_csv(sectoralEmissionsPath).to_dict(orient="records")[0]["electricity"] * 1e9
    )
    electricityFacilities = pd.read_csv(electricityPath, header=0).to_dict(orient="records")
    totalCapacity = sum(item["capacity"] for item in electricityFacilities)
    landmask = ds["LANDMASK"][:]

    _, lmy, lmx = landmask.shape
    ww = ds.DX * lmx
    hh = ds.DY * lmy

    methane = np.zeros(landmask.shape)

    for facility in electricityFacilities:
        x, y = domainProj(facility["lng"], facility["lat"])
        ix = math.floor((x + ww / 2) / ds.DX)
        iy = math.floor((y + hh / 2) / ds.DY)
        try:
            methane[0][iy][ix] += (facility["capacity"] / totalCapacity) * electricityEmis
        except IndexError:
            pass  # it's outside our domain

    write_layer("OCH4_ELECTRICITY", convert_to_timescale(methane))


if __name__ == "__main__":
    processEmissions()
    sumLayers()
