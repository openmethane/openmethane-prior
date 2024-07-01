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

"""Utilities related to GEOJSON files"""

import json

import netCDF4 as nc
import numpy as np
from geojson import Feature, FeatureCollection, Polygon, dumps
from openmethane_prior.omOutputs import domainOutputPath, geoJSONOutputPath

prior_layers = [
    "OCH4_AGRICULTURE",
    "OCH4_LULUCF",
    "OCH4_WASTE",
    "OCH4_LIVESTOCK",
    "OCH4_INDUSTRIAL",
    "OCH4_STATIONARY",
    "OCH4_TRANSPORT",
    "OCH4_ELECTRICITY",
    "OCH4_FUGITIVE",
    "OCH4_TERMITE",
    "OCH4_FIRE",
    "OCH4_WETLANDS",
    "OCH4_TOTAL",
]

class NumpyEncoder(json.JSONEncoder):
    """Numpy encoder for JSON serialization"""

    def default(self, obj):  # noqa: D102
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


def processGeoJSON():
    """Convert the gridded prior to GeoJSON format"""
    print("converting gridded prior to GeoJSON")

    # Load domain
    print("Loading output file")
    ds = nc.Dataset(domainOutputPath)

    # There is a better way to do this but this will work for now
    # Using xarray wasn't straightforward because the layers don't use
    # the same attribute names, ie mixing x/y and lat/long.
    ds_slice = {
        "LANDMASK": ds["LANDMASK"][:][0],
        "LATD": ds["LATD"][:][0][0],
        "LOND": ds["LOND"][:][0][0],
    }

    max_values = {}
    for layer_name in prior_layers:
        # extract the meaningful dimensions from the NetCDF variables
        ds_slice[layer_name] = ds[layer_name][:][0][0]
        # find the max emission value in a single cell for each layer
        max_values[layer_name] = np.max(ds_slice[layer_name])

    # Add GeoJSON Polygon feature for each grid location
    features = []

    print("Gathering cell data")
    for (y, x), _ in np.ndenumerate(ds_slice["LANDMASK"]):
        properties={
            "x": x,
            "y": y,
            "landmask": int(ds_slice["LANDMASK"][y][x]),
            # left for backward compatibility with previous format
            "m": float(ds_slice["OCH4_TOTAL"][y][x]),
            "rm": float(ds_slice["OCH4_TOTAL"][y][x] / max_values["OCH4_TOTAL"]),
        }
        for layer_name in prior_layers:
            # raw values
            properties[layer_name] = float(ds_slice[layer_name][y][x])
            # relative to max
            properties[f"{layer_name}_R"] = float(ds_slice[layer_name][y][x] / max_values[layer_name])

        features.append(
            Feature(
                geometry=Polygon(
                    (
                        [
                            (float(ds_slice["LOND"][y][x]), float(ds_slice["LATD"][y][x])),
                            (float(ds_slice["LOND"][y][x + 1]), float(ds_slice["LATD"][y][x + 1])),
                            (float(ds_slice["LOND"][y + 1][x + 1]), float(ds_slice["LATD"][y + 1][x + 1])),
                            (float(ds_slice["LOND"][y + 1][x]), float(ds_slice["LATD"][y + 1][x])),
                            (float(ds_slice["LOND"][y][x]), float(ds_slice["LATD"][y][x])),
                        ],
                    )
                ),
                properties=properties,
            )
        )

    feature_collection = FeatureCollection(features)

    print("Writing output to", geoJSONOutputPath)
    with open(geoJSONOutputPath, "w") as fp:
        fp.write(dumps(feature_collection))


if __name__ == "__main__":
    processGeoJSON()
