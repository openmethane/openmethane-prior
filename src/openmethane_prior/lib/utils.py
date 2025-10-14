#
# Copyright 2023 The Superpower Institute Ltd.
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

"""General utilities"""

import cftime
import datetime
import gzip
import importlib
import os
import pathlib
import pickle
import sys
import typing

import numpy as np
from numpy.typing import ArrayLike
from urllib.parse import urlparse
import xarray as xr

T = typing.TypeVar("T", bound=ArrayLike | float)


SECS_PER_YEAR = 365 * 24 * 60 * 60


def save_zipped_pickle(obj, filename: str | pathlib.Path, protocol=-1):
    """Save a compressed pickle file."""
    pathlib.Path(filename).parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(filename, "wb") as f:
        pickle.dump(obj, f, protocol)


def load_zipped_pickle(filename: str | pathlib.Path):
    """Load a gzipped pickle file from disk.

    Parameters
    ----------
    filename
        Filename of the gzipped pickle file to load
    """
    with gzip.open(filename, "rb") as f:
        loaded_object = pickle.load(f)  # noqa: S301
    return loaded_object


def area_of_rectangle_m2(lat1: T, lat2: T, lon1: T, lon2: T) -> T:
    """Calculate the area of a latitude/longitude rectangle, returning the result in m^2.

    Parameters
    ----------
    lat1
        Latitude of one corner
    lat2
        Latitude of the diagonally opposite corner
    lon1
        Longitude of one corner
    lon2
        Longitude of the diagonally opposite corner

    Returns
    -------
        Area in units of m^2
    """
    lat_radians = np.pi * lat1 / 180.0
    lon_radians = np.pi * lat2 / 180.0
    coef = 708422.8776524838  ## (np.pi/180.0) * R**2
    area = coef * np.abs(np.sin(lat_radians) - np.sin(lon_radians)) * np.abs(lon1 - lon2) * 1e6
    return area


def redistribute_spatially(lat_shape, ind_x, ind_y, coefs, subset, from_areas, to_areas):  # noqa: PLR0913
    """Redistribute GFAS emissions horizontally and vertically.

    This little function does most of the work.

    Parameters
    ----------
    lat_shape
        Shape of the LAT variable
    ind_x
        x-indices in the GFAS domain corresponding to indices in the CMAQ domain
    ind_y
        y-indices in the GFAS domain corresponding to indices in the CMAQ domain
    coefs
        Area-weighting coefficients to redistribute the emissions
    subset
        Emissions to distribute
    from_areas
        Areas of input grid-cells in units of m^2
    to_areas
        Area of output grid-cells in units of m^2

    Returns
    -------
        gridded: concentrations on the 2D CMAQ grid

    """
    ##
    gridded = np.zeros(lat_shape, dtype=np.float32)
    ij = 0
    for i in range(lat_shape[0]):
        for j in range(lat_shape[1]):
            ij += 1
            for k in range(len(ind_x[ij])):
                ix = ind_x[ij][k]
                iy = ind_y[ij][k]
                gridded[i, j] += subset[iy, ix] * coefs[ij][k] * from_areas[iy, ix]
    gridded /= to_areas
    return gridded


def get_command():
    return " ".join(sys.argv)


def get_timestamped_command():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    return f"{now_utc.isoformat(sep=' ', timespec='seconds')}: {get_command()}"


def get_version():
    return os.getenv('OPENMETHANE_PRIOR_VERSION', importlib.metadata.version('openmethane_prior'))


def time_bounds(
    dates: xr.CFTimeIndex,
    interval: datetime.timedelta = datetime.timedelta(days=1)
) -> list[list[cftime.datetime]]:
    bounds = []
    for period_start in dates:
        # bounds for each time coordinate extend from the start
        # to the end of the interval
        bounds.append([period_start, period_start + interval])
    return bounds


def datetime64_to_datetime( dt: np.datetime64) -> datetime.datetime:
    """ converts a datetime64 object into a datetime.datetime object.
    borrows from https://stackoverflow.com/questions/13703720/converting-between-datetime-timestamp-and-datetime64 """
    epoch = np.datetime64(0,'s')
    one_second = np.timedelta64(1,'s')
    seconds_since_epoch = (dt - epoch)/one_second
    return datetime.datetime.utcfromtimestamp(seconds_since_epoch)
    

def bounds_from_cell_edges(cell_edges: xr.DataArray) -> np.array:
    """
    Convert an array with [n+1] elements representing the edge coordinates of
    grid cells, to an array of [n][2] elements where each entry contains the
    lower and upper edge of the grid cell at position n.
    """
    lower_bounds = cell_edges[:-1]
    upper_bounds = cell_edges[1:]
    return np.column_stack([lower_bounds, upper_bounds])


def list_cf_grid_mappings(
    ds: xr.Dataset,
) -> list[str]:
    """
    Return a list variables in a Dataset which contain a grid mapping.

    See: https://cfconventions.org/cf-conventions/cf-conventions.html#appendix-grid-mappings
    :param ds: An xarray.Dataset object which follows CF conventions.
    :return:
    """
    # find any variables containing grid mapping details
    grid_mappings = []
    for var in ds.data_vars:
        if "grid_mapping_name" in ds[var].attrs:
            grid_mappings.append(var)
    return grid_mappings


def is_url(maybe_url: str) -> bool:
    """
    Returns true if the provided string is formatted like a valid URL.
    :param maybe_url: string to check
    :return:
    """
    parsed = urlparse(maybe_url)
    return parsed.scheme != "" and parsed.netloc != ""
