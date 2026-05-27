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
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon

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


def grid_weights_from_linestring(
    grid: Grid,
    linestring: MultiLineString | LineString,
):
    """Returns a weighted grid mask indicating how much length of a linestring
    intersects with each grid cell.

    The linestring must be in the same coordinate system as the grid.

    A MultiLineString represents a collection of linestrings and is handled
    identically — pass ``shapely.union_all(gdf.geometry.values)`` to use a
    GeoDataFrame geometry column directly.

    Weights are normalised by the total linestring length, so they sum to 1
    when the linestring lies entirely within the grid and to less than 1 when
    part of it falls outside the domain.

    :param grid: Grid to construct the mask for
    :param linestring: LineString or MultiLineString in the grid's coordinate system
    :return: Gridded mask with float values representing the fraction of the
        linestring's total length that intersects each grid cell.
    """
    total_length = shapely.length(linestring)
    if total_length == 0:
        return np.zeros(grid.shape)

    bx = grid.cell_bounds_x()  # (nx+1,)
    by = grid.cell_bounds_y()  # (ny+1,)

    cell_ix, cell_iy = np.meshgrid(
        np.arange(grid.dimensions[0]),
        np.arange(grid.dimensions[1]),
    )  # both (ny, nx)

    # vectorised cell boxes, flattened to (ny*nx,)
    boxes: np.ndarray = np.asarray(shapely.box(
        bx[cell_ix].ravel(), by[cell_iy].ravel(),
        bx[cell_ix + 1].ravel(), by[cell_iy + 1].ravel(),
    ))

    # spatial index avoids O(ny*nx) intersection calls
    tree = shapely.STRtree(boxes)
    candidate_indices = tree.query(linestring, predicate="intersects")

    weights = np.zeros(len(boxes))
    if len(candidate_indices) > 0:
        intersections = shapely.intersection(boxes[candidate_indices], linestring)
        weights[candidate_indices] = shapely.length(intersections)

    return weights.reshape(grid.shape) / total_length
