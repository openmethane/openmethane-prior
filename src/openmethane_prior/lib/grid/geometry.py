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
import numpy as np
import shapely
from shapely.geometry import MultiPolygon, Polygon

from .grid import Grid


def grid_mask_from_polygon(
    grid: Grid,
    polygon: MultiPolygon | Polygon,
):
    """Returns a boolean grid mask indicating which grid cells fall inside the
    provided polygon. Assumes that a grid center point intersecting the polygon
    is considered "inside", does not attempt any grid cell area weighting.

    The polygon must be in the same coordinate system as the grid.

    :param grid: Grid to construct the mask for
    :param polygon: Polygon shape in the grid's coordinate system
    :return: Gridded mask with True in cells with a centre point inside the
        polygon.
    """
    xs = grid.cell_coords_x()  # (nx,)
    ys = grid.cell_coords_y()  # (ny,)
    xx, yy = np.meshgrid(xs, ys)  # both (ny, nx)
    return shapely.contains_xy(polygon, xx.ravel(), yy.ravel()).reshape(grid.shape)
