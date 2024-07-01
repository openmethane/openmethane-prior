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

        "OCH4_AGRICULTURE": ds["OCH4_AGRICULTURE"][:][0][0],
        "OCH4_LULUCF": ds["OCH4_LULUCF"][:][0][0],
        "OCH4_WASTE": ds["OCH4_WASTE"][:][0][0],
        "OCH4_LIVESTOCK": ds["OCH4_LIVESTOCK"][:][0][0],
        "OCH4_INDUSTRIAL": ds["OCH4_INDUSTRIAL"][:][0][0],
        "OCH4_STATIONARY": ds["OCH4_STATIONARY"][:][0][0],
        "OCH4_TRANSPORT": ds["OCH4_TRANSPORT"][:][0][0],
        "OCH4_ELECTRICITY": ds["OCH4_ELECTRICITY"][:][0][0],
        "OCH4_FUGITIVE": ds["OCH4_FUGITIVE"][:][0][0],
        "OCH4_TERMITE": ds["OCH4_TERMITE"][:][0][0],
        "OCH4_FIRE": ds["OCH4_FIRE"][:][0][0],
        "OCH4_WETLANDS": ds["OCH4_WETLANDS"][:][0][0],
        "OCH4_TOTAL": ds["OCH4_TOTAL"][:][0][0],
    }

    print("Finding max emission for each layer")
    max_values = {
        "OCH4_AGRICULTURE": np.amax(ds_slice["OCH4_AGRICULTURE"]),
        "OCH4_LULUCF": np.amax(ds_slice["OCH4_LULUCF"]),
        "OCH4_WASTE": np.amax(ds_slice["OCH4_WASTE"]),
        "OCH4_LIVESTOCK": np.amax(ds_slice["OCH4_LIVESTOCK"]),
        "OCH4_INDUSTRIAL": np.amax(ds_slice["OCH4_INDUSTRIAL"]),
        "OCH4_STATIONARY": np.amax(ds_slice["OCH4_STATIONARY"]),
        "OCH4_TRANSPORT": np.amax(ds_slice["OCH4_TRANSPORT"]),
        "OCH4_ELECTRICITY": np.amax(ds_slice["OCH4_ELECTRICITY"]),
        "OCH4_FUGITIVE": np.amax(ds_slice["OCH4_FUGITIVE"]),
        "OCH4_TERMITE": np.amax(ds_slice["OCH4_TERMITE"]),
        "OCH4_FIRE": np.amax(ds_slice["OCH4_FIRE"]),
        "OCH4_WETLANDS": np.amax(ds_slice["OCH4_WETLANDS"]),
        "OCH4_TOTAL": np.amax(ds_slice["OCH4_TOTAL"]),
    }

    # Add GeoJSON Polygon feature for each grid location
    features = []

    print("Gathering cell data")
    for (y, x), _ in np.ndenumerate(ds_slice["LANDMASK"]):
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
                properties={
                    "x": x,
                    "y": y,
                    "landmask": int(ds_slice["LANDMASK"][y][x]),
                    
                    # raw values
                    "OCH4_AGRICULTURE": float(ds_slice["OCH4_AGRICULTURE"][y][x]),
                    "OCH4_LULUCF": float(ds_slice["OCH4_LULUCF"][y][x]),
                    "OCH4_WASTE": float(ds_slice["OCH4_WASTE"][y][x]),
                    "OCH4_LIVESTOCK": float(ds_slice["OCH4_LIVESTOCK"][y][x]),
                    "OCH4_INDUSTRIAL": float(ds_slice["OCH4_INDUSTRIAL"][y][x]),
                    "OCH4_STATIONARY": float(ds_slice["OCH4_STATIONARY"][y][x]),
                    "OCH4_TRANSPORT": float(ds_slice["OCH4_TRANSPORT"][y][x]),
                    "OCH4_ELECTRICITY": float(ds_slice["OCH4_ELECTRICITY"][y][x]),
                    "OCH4_FUGITIVE": float(ds_slice["OCH4_FUGITIVE"][y][x]),
                    "OCH4_TERMITE": float(ds_slice["OCH4_TERMITE"][y][x]),
                    "OCH4_FIRE": float(ds_slice["OCH4_FIRE"][y][x]),
                    "OCH4_WETLANDS": float(ds_slice["OCH4_WETLANDS"][y][x]),
                    "OCH4_TOTAL": float(ds_slice["OCH4_TOTAL"][y][x]),
                    "m": float(ds_slice["OCH4_TOTAL"][y][x]),

                    # relative to max
                    "OCH4_AGRICULTURE_R": float(ds_slice["OCH4_AGRICULTURE"][y][x] / max_values["OCH4_AGRICULTURE"]),
                    "OCH4_LULUCF_R": float(ds_slice["OCH4_LULUCF"][y][x] / max_values["OCH4_LULUCF"]),
                    "OCH4_WASTE_R": float(ds_slice["OCH4_WASTE"][y][x] / max_values["OCH4_WASTE"]),
                    "OCH4_LIVESTOCK_R": float(ds_slice["OCH4_LIVESTOCK"][y][x] / max_values["OCH4_LIVESTOCK"]),
                    "OCH4_INDUSTRIAL_R": float(ds_slice["OCH4_INDUSTRIAL"][y][x] / max_values["OCH4_INDUSTRIAL"]),
                    "OCH4_STATIONARY_R": float(ds_slice["OCH4_STATIONARY"][y][x] / max_values["OCH4_STATIONARY"]),
                    "OCH4_TRANSPORT_R": float(ds_slice["OCH4_TRANSPORT"][y][x] / max_values["OCH4_TRANSPORT"]),
                    "OCH4_ELECTRICITY_R": float(ds_slice["OCH4_ELECTRICITY"][y][x] / max_values["OCH4_ELECTRICITY"]),
                    "OCH4_FUGITIVE_R": float(ds_slice["OCH4_FUGITIVE"][y][x] / max_values["OCH4_FUGITIVE"]),
                    "OCH4_TERMITE_R": float(ds_slice["OCH4_TERMITE"][y][x] / max_values["OCH4_TERMITE"]),
                    "OCH4_FIRE_R": float(ds_slice["OCH4_FIRE"][y][x] / max_values["OCH4_FIRE"]),
                    "OCH4_WETLANDS_R": float(ds_slice["OCH4_WETLANDS"][y][x] / max_values["OCH4_WETLANDS"]),
                    "OCH4_TOTAL_R": float(ds_slice["OCH4_TOTAL"][y][x] / max_values["OCH4_TOTAL"]),
                    "rm": float(ds_slice["OCH4_TOTAL"][y][x] / max_values["OCH4_TOTAL"]),
                },
            )
        )

    feature_collection = FeatureCollection(features)

    print("Writing output to", geoJSONOutputPath)
    with open(geoJSONOutputPath, "w") as fp:
        fp.write(dumps(feature_collection))


if __name__ == "__main__":
    processGeoJSON()
