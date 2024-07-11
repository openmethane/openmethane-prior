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

"""Generate a JSON file describing the domain and grid."""

import json

import numpy as np

from openmethane_prior.config import PriorConfig, load_config_from_env


def _make_point(x, y):
    return [float(x), float(y)]


def write_domain_json(config: PriorConfig, output_file):
    """
    Write a JSON file describing the domain and grid.

    The JSON file contains the following information:
    * CRS description
    * Grid properties (number of rows, columns, cell size, and center lat/lon)
    * List of grid cells, each with the following properties:
        * Projection x and y coordinates
        * Landmask value
        * Center lat/lon
        * Corner lat/lon values

    This file is ingested by the frontend and is static for a given domain.

    Parameters
    ----------
    output_file
        File to read
    """
    # Load raster land-use data
    print("converting domain grid details to JSON")

    domain_ds = config.domain_dataset()

    domain = {
        "crs": {
            "projection_type": "lambert_conformal_conic",
            "standard_parallel": float(domain_ds.attrs["TRUELAT1"]),
            "standard_parallel_2": float(domain_ds.attrs["TRUELAT2"]),
            "longitude_of_central_meridian": float(domain_ds.attrs["STAND_LON"]),
            "latitude_of_projection_origin": float(domain_ds.attrs["MOAD_CEN_LAT"]),
            "projection_origin_x": float(domain_ds.attrs["XORIG"]),
            "projection_origin_y": float(domain_ds.attrs["YORIG"]),
            "proj4": config.domain_projection().to_proj4(),
        },
        "grid_properties": {
            "rows": domain_ds.sizes["ROW"],
            "cols": domain_ds.sizes["COL"],
            "cell_x_size": float(domain_ds.attrs["DX"]),
            "cell_y_size": float(domain_ds.attrs["DY"]),
            "center_latlon": _make_point(domain_ds.attrs["XCENT"], domain_ds.attrs["YCENT"]),
        },
        "grid_cells": [],
    }

    if (
        domain_ds.sizes["ROW_D"] != domain_ds.sizes["ROW"] + 1
        or domain_ds.sizes["COL_D"] != domain_ds.sizes["COL"] + 1
    ):
        raise RuntimeError("Cell corners dimension must be one greater than number of cells")

    domain_slice = domain_ds.sel(TSTEP=0, LAY=0)
    # Add projection coordinates and WGS84 lat/lon for each grid cell
    for (y, x), _ in np.ndenumerate(domain_slice["LANDMASK"]):
        cell_properties = {
            "projection_x_coordinate": int(x),
            "projection_y_coordinate": int(y),
            "landmask": int(domain_slice["LANDMASK"].item(y, x)),
            "center_latlon": _make_point(
                domain_slice["LAT"].item(y, x), domain_slice["LON"].item(y, x)
            ),
            "corner_latlons": [
                _make_point(domain_slice["LATD"].item(y, x), domain_slice["LOND"].item(y, x)),
                _make_point(
                    domain_slice["LATD"].item(y, x + 1), domain_slice["LOND"].item(y, x + 1)
                ),
                _make_point(
                    domain_slice["LATD"].item(y + 1, x + 1), domain_slice["LOND"].item(y + 1, x + 1)
                ),
                _make_point(
                    domain_slice["LATD"].item(y + 1, x), domain_slice["LOND"].item(y + 1, x)
                ),
            ],
        }
        domain["grid_cells"].append(cell_properties)

    json.dump(domain, output_file)


if __name__ == "__main__":
    config = load_config_from_env()
    output_file = config.as_output_file("om-domain.json")

    with open(output_file, "w") as fp:
        write_domain_json(config, fp)
