#
# Copyright 2025 The Superpower Institute Ltd.
#
# This file is part of Open Methane.
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

import pyproj
import xarray as xr

from .grid import Grid
from ..utils import list_cf_grid_mappings


def create_grid_from_domain(
    domain_ds: xr.Dataset
) -> Grid:
    """
    Make a Grid object from a prior domain dataset.
    """
    # find the domain variable containing the grid mapping
    grid_mapping = list_cf_grid_mappings(domain_ds)[0]

    return Grid(
        dimensions=(domain_ds.sizes["x"], domain_ds.sizes["y"]),
        origin_xy=(domain_ds.XORIG, domain_ds.YORIG),
        cell_size=(domain_ds.XCELL, domain_ds.YCELL),
        proj_params=pyproj.CRS.from_cf(domain_ds[grid_mapping].attrs),
    )


def create_grid_from_mcip(
    TRUELAT1: float,
    TRUELAT2: float,
    MOAD_CEN_LAT: float,
    STAND_LON: float,
    COLS: int,
    ROWS: int,
    XCENT: float,
    YCENT: float,
    XORIG: float,
    YORIG: float,
    XCELL: float,
    YCELL: float,
) -> Grid:
    """
    Make a Grid object from attributes that will be present in WRF geometry
    files and MCIP DOT files.
    """
    # if the domain was generated from WRF geometry, we must use a
    # spherical Earth in our projection.
    # https://fabienmaussion.info/2018/01/06/wrf-projection/
    # TODO: allow these params to be specified for non-WRF domains
    earth_equatorial_axis_radius = 6370000
    earth_polar_axis_radius = 6370000
    proj_params = dict(
        proj="lcc",
        lat_1=TRUELAT1,
        lat_2=TRUELAT2,
        lat_0=MOAD_CEN_LAT,
        lon_0=STAND_LON,
        # semi-major or equatorial axis radius
        a=earth_equatorial_axis_radius,
        # semi-minor, or polar axis radius
        b=earth_polar_axis_radius,
    )

    # WRF records the grid centre coords in lon/lat as XCENT/YCENT
    # pyproj and CF conventions need these in grid units, so we create
    # a naive projection with the other parameters and convert them
    naive_projection = pyproj.Proj(**proj_params)
    false_easting, false_northing = naive_projection(longitude=XCENT, latitude=YCENT)
    proj_params_adjusted = proj_params | dict(
        x_0=-false_easting,
        y_0=-false_northing,
    )

    return Grid(
        dimensions=(COLS, ROWS),
        origin_xy=(XORIG, YORIG),
        cell_size=(XCELL, YCELL),
        proj_params=proj_params_adjusted,
    )
