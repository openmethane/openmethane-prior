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
Utilities related to GEOJSON files
"""

import numpy as np
import netCDF4 as nc
from omOutputs import domainOutputPath, geoJSONOutputPath, ch4JSONOutputPath
import json
from geojson import Feature, Polygon, FeatureCollection, dumps

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)
    
def processGeoJSON():
    # Load raster land-use data
    print("converting gridded prior to GeoJSON")

    # Load domain
    print("Loading output file")
    ds = nc.Dataset(domainOutputPath)
    landmask = ds["LANDMASK"][:]
    lats = ds["XLAT_C"][:]
    longs = ds["XLONG_C"][:]
    ch4 = ds["OCH4_TOTAL"][:][0]
    maxEmission = np.amax(ch4)

    # Add GeoJSON Polygon feature for each grid location

    methane = np.zeros((landmask.shape[1], landmask.shape[2]), dtype=np.int32)
    features = []

    for (y, x), _ in np.ndenumerate(landmask[0]):
        methane[y][x] = ch4[y][x]
        features.append(
            Feature(
                geometry=Polygon(
                    [
                        [
                            (float(longs[0][y][x]), float(lats[0][y][x])),
                            (float(longs[0][y][x + 1]), float(lats[0][y][x + 1])),
                            (float(longs[0][y + 1][x + 1]), float(lats[0][y + 1][x + 1])),
                            (float(longs[0][y + 1][x]), float(lats[0][y + 1][x])),
                            (float(longs[0][y][x]), float(lats[0][y][x])),
                        ]
                    ]
                ),
                properties={
                    "x": x,
                    "y": y,
                    "m": float(methane[y][x]),
                    "rm": float(methane[y][x] / maxEmission * 100)
                    if methane[y][x] >= 0
                    else 0,
                },
            )
        )


    feature_collection = FeatureCollection(features)
    with open(geoJSONOutputPath, "w") as fp:
        fp.write(dumps(feature_collection))

    with open(ch4JSONOutputPath, "w") as fp:
        json.dump(methane, fp, cls=NumpyEncoder)


if __name__ == '__main__':
    processGeoJSON()