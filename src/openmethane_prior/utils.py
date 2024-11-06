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
import pathlib
import pickle
import typing

import numpy as np
from numpy.typing import ArrayLike

from openmethane_prior.config import PriorConfig

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


def domain_cell_index(config: PriorConfig, lons, lats,
                      transform=None) -> tuple[int, int]:
    """Calculate indices in cell of lat,lon point(s)"""
    llc_x, llc_y = config.llc_xy()  # lower left corner in x,y coords
    if transform is None:
        transform = config.domain_projection()
    x, y = transform(lons, lats)
    # calculate indices  assuming regular grid
    ix = np.floor((x - llc_x) / config.domain_dataset().XCELL).astype("int")
    iy = np.floor((y - llc_y) / config.domain_dataset().YCELL).astype("int")
    return ix, iy
