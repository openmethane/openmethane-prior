#
# Copyright 2023-2024 The Superpower Institute Ltd.
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
General utilties
"""

import datetime
import gzip
import os
import pickle

import dotenv
import numpy as np

dotenv.load_dotenv()
getenv = os.environ.get

secsPerYear = 365 * 24 * 60 * 60


def date_time_range(start: datetime.date, end: datetime.date, delta: datetime.timedelta):
    """Iterate over a range of dates between start and end.

    Args:
    ----
        start: Start date (inclusive)
        end: Start date (exclusive)
        delta: Time delta to step over

    Yields:
    ------
        Dates between start and end (exclusive)

    """
    t = start
    while t < end:
        yield t
        t += delta


def save_zipped_pickle(obj, filename, protocol=-1):
    """Save a compressed pickle file."""
    with gzip.open(filename, "wb") as f:
        pickle.dump(obj, f, protocol)


def load_zipped_pickle(filename):
    """Load a gzipped pickle file from disk.

    Args:
    ----
        filename: filename of the gzipped pickle file to load

    """
    with gzip.open(filename, "rb") as f:
        loaded_object = pickle.load(f)  # noqa: S301
    return loaded_object


def area_of_rectangle_m2(lat1, lat2, lon1, lon2):
    """Calculate the area of a latitude/longitude rectangle, returning the result in m^2.

    Args:
    ----
        lat1: Latitude of one corner
        lat2: Latitude of the diagonally opposite corner
        lon1: Longitude of one corner
        lon2: Longitude of the diagonally opposite corner

    Returns:
    -------
        A: area in units of m^2

    """
    LAT1 = np.pi * lat1 / 180.0
    LAT2 = np.pi * lat2 / 180.0
    # LON1 = np.pi*lon1/180.0
    # LON2 = np.pi*lon2/180.0
    coef = 708422.8776524838  ## (np.pi/180.0) * R**2
    A = coef * np.abs(np.sin(LAT1) - np.sin(LAT2)) * np.abs(lon1 - lon2) * 1e6
    return A


def redistribute_spatially(LATshape, ind_x, ind_y, coefs, subset, fromAreas, toAreas): # noqa: PLR0913
    """Redistribute GFAS emissions horizontally and vertically.

    This little function does most of the work.

    Args:
    ----
        LATshape: shape of the LAT variable
        ind_x: x-indices in the GFAS domain corresponding to indices in the CMAQ domain
        ind_y: y-indices in the GFAS domain corresponding to indices in the CMAQ domain
        coefs: Area-weighting coefficients to redistribute the emissions
        subset: the GFAS emissions
        fromAreas: Areas of input grid-cells in units of m^2
        toAreas: area of output gridcells in units of m^2

    Returns:
    -------
        gridded: concentrations on the 2D CMAQ grid

    """
    ##
    gridded = np.zeros(LATshape, dtype=np.float32)
    ij = 0
    for i in range(LATshape[0]):
        for j in range(LATshape[1]):
            ij += 1
            for k in range(len(ind_x[ij])):
                ix = ind_x[ij][k]
                iy = ind_y[ij][k]
                gridded[i, j] += subset[iy, ix] * coefs[ij][k] * fromAreas[iy, ix]
    gridded /= toAreas
    return gridded
