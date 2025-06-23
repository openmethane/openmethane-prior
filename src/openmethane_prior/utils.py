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

"""General utilities"""

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
import xarray as xr

T = typing.TypeVar("T", bound=ArrayLike | float)


SECS_PER_YEAR = 365 * 24 * 60 * 60


def date_time_range(start: datetime.date, end: datetime.date, delta: datetime.timedelta):
    """Iterate over a range of dates between start and end.

    Parameters
    ----------
    start
        Start date (inclusive)
    end
        Start date (exclusive)
    delta
        Time delta to step over

    Yields
    ------
        Dates between start and end (exclusive)

    """
    t = start
    while t < end:
        yield t
        t += delta


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


def time_bounds(dates: xr.CFTimeIndex):
    bounds = []
    for period_start in dates:
        # bounds for each day start at midnight and extend 1 day
        bounds.append([
            period_start,
            period_start + datetime.timedelta(days=1)
        ])
    return bounds


def extract_bounds(corner_coords: xr.DataArray):
    """
    Extract grid cell boundary coordinates for a single dimension, from a 2D
    array of size x+1,y+1 where x,y are the grid cell coordinates.
    An array describing the corners of a 2x2 grid would have 3x3 items, where
    the corners of the cell at [0][0] would be: [0][0], [1][0], [1][1], [0][1]

    See: https://cfconventions.org/Data/cf-conventions/cf-conventions-1.11/cf-conventions.html#cell-boundaries

    Parameters:
    corner_coords: xarray.DataArray with dimensions like ('y_corner', 'x_corner')
                  containing coordinate values at grid corners
                  Shape: (ny_corners, nx_corners) where corners = cells + 1

    Returns:
    xarray.DataArray with dimensions ('y', 'x', 'corner') where:
    - y has size ny_corners - 1 (number of cells)
    - x has size nx_corners - 1 (number of cells)
    - corner has 4 values representing the corners of each cell
    """
    if len(corner_coords.shape) < 2:
        raise ValueError("corner coordinates must have at least 2 dimensions")

    # Get corner data as numpy array for efficient indexing
    corner_data = corner_coords.values
    ny_corners, nx_corners = corner_data.shape[-2:]
    ny_cells, nx_cells = ny_corners - 1, nx_corners - 1

    # Create output array
    cell_corners = np.zeros((ny_cells, nx_cells, 4))

    # Vectorized assignment of all corners
    cell_corners[:, :, 0] = corner_data[:-1, :-1]  # bottom_left
    cell_corners[:, :, 1] = corner_data[:-1, 1:]   # bottom_right
    cell_corners[:, :, 2] = corner_data[1:, 1:]    # top_right
    cell_corners[:, :, 3] = corner_data[1:, :-1]   # top_left

    # Create new DataArray
    result = xr.DataArray(
        cell_corners,
        coords={
            "y": range(ny_cells),
            "x": range(nx_cells),
            "corner": ["bottom_left", "bottom_right", "top_right", "top_left"]
        },
    )

    return result