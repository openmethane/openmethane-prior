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
from shapely import Polygon, MultiPolygon
import typing

from .grid import Grid

# a cell intersection is a tuple containing a coordinate tuple, and a fraction
# of intersection, representing how much of a shape falls within each cell.
CellIntersection = typing.TypeVar("CellIntersection", bound=tuple[tuple[float, float], float])

def polygon_cell_intersection(
    geometry: Polygon | MultiPolygon,
    grid: Grid,
) -> list[CellIntersection]:
    """Determine which grid cells a polygon intersects with, returning a list
    of grid cell indexes and their ratio of intersection with the polygon.

    Polygon shapes should have their coordinates specified in lat/lon in
    the same CRS used by the Grid."""
    # find the smallest area of the grid to examine based on the bounding box
    bounds_llc_lon, bounds_llc_lat, bounds_urc_lon, bounds_urc_lat = geometry.bounds
    bbox_ix, bbox_iy, _ = grid.lonlat_to_cell_index(
        np.array([bounds_llc_lon, bounds_urc_lon, bounds_urc_lon, bounds_llc_lon]),
        np.array([bounds_llc_lat, bounds_llc_lat, bounds_urc_lat, bounds_urc_lat]),
    )
    min_ix, max_ix = np.min(bbox_ix), np.max(bbox_ix)
    min_iy, max_iy = np.min(bbox_iy), np.max(bbox_iy)

    cell_bounds_lon, cell_bounds_lat = grid.cell_bounds_lonlat()

    intersections: list[CellIntersection] = []
    for iy in range(min_iy, max_iy + 1):
        for ix in range(min_ix, max_ix + 1):
            # if part of the shape falls outside the grid, skip those areas
            if not grid.valid_cell_coords(ix, iy):
                continue

            # find the intersection between the geometry and the grid cell
            cell_polygon = Polygon(zip(cell_bounds_lon[iy, ix], cell_bounds_lat[iy, ix]))
            intersection = geometry.intersection(cell_polygon)

            if intersection is not None and intersection.area > 0:
                intersections.append(((ix, iy), intersection.area / geometry.area))

    return intersections
