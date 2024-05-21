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
Generate a JSON file describing the domain and grid.
"""

import numpy as np
import netCDF4 as nc
from omInputs import domainXr, domainProj
from omOutputs import domainJSONOutputPath
import json

def makePoint(x, y):
    return ([float(x), float(y)])

def writeDomainJSON():
    # Load raster land-use data
    print("converting domain grid details to JSON")

    domain = {
        "crs": {
            "projection_type": "lambert_conformal_conic",
            "standard_parallel": float(domainXr.attrs['TRUELAT1']),
            "standard_parallel_2": float(domainXr.attrs['TRUELAT2']),
            "longitude_of_central_meridian": float(domainXr.attrs['STAND_LON']),
            "latitude_of_projection_origin": float(domainXr.attrs['MOAD_CEN_LAT']),
            "proj4": domainProj.to_proj4(),
        },
        "grid_properties": {
            "rows": domainXr.sizes['ROW'],
            "cols": domainXr.sizes['COL'],
            "cell_x_size": float(domainXr.attrs['DX']),
            "cell_y_size": float(domainXr.attrs['DY']),
        },
        "grid_cells": [],
    };

    if domainXr.sizes['ROW_D'] != domainXr.sizes['ROW'] + 1 or domainXr.sizes['COL_D'] != domainXr.sizes['COL'] + 1:
      raise Exception('Cell corners dimension must be one greater than number of cells')

    # Add projection coordinates and WGS84 lat/lon for each grid cell
    for (y, x), _ in np.ndenumerate(domainXr["LANDMASK"][0]):
        cell_properties = {
            "projection_x_coordinate": int(x),
            "projection_y_coordinate": int(y),
            "landmask": int(domainXr["LANDMASK"].item(0, y, x)),
            "center_latlon": makePoint(domainXr["LAT"].item(0, y, x), domainXr["LON"].item(0, y, x)),
            "corner_latlons": [
              makePoint(domainXr["LATD"].item(0, 0, y, x),         domainXr["LOND"].item(0, 0, y, x)),
              makePoint(domainXr["LATD"].item(0, 0, y, x + 1),     domainXr["LOND"].item(0, 0, y, x + 1)),
              makePoint(domainXr["LATD"].item(0, 0, y + 1, x + 1), domainXr["LOND"].item(0, 0, y + 1, x + 1)),
              makePoint(domainXr["LATD"].item(0, 0, y + 1, x),     domainXr["LOND"].item(0, 0, y + 1, x)),
            ],
        }
        domain["grid_cells"].append(cell_properties);

    with open(domainJSONOutputPath, "w") as fp:
        json.dump(domain, fp)

if __name__ == '__main__':
    writeDomainJSON()