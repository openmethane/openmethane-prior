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
import itertools
import numpy as np
import pyproj
from shapely import geometry

from .grid import Grid
import openmethane_prior.lib.logger as logger

logger = logger.get_logger(__name__)

def regrid_data(
    data: np.ndarray,
    from_grid: Grid,
    to_grid: Grid,
) -> np.ndarray:
    """
    Re-grids a dataset to a shape defined by to_grid, using a nearest neighbor
    strategy. Values are **not** conserved, so this is mostly useful for masks.
    :param data: 2d gridded data
    :param from_grid: Grid of the source data
    :param to_grid: Target grid to reshape the data to
    :return: 2d dataset of gridded cell values in the target grid
    """
    # if grids are exactly the same, no regridding is necessary
    if from_grid == to_grid:
        logger.debug("identical grids, skip regridding")
        return data

    # if grids share the same base projection, we can apply an efficient
    # regridding method using np.digitize
    if to_grid.is_aligned(from_grid):
        logger.debug("aligned grids, fast regridding")
        return regrid_aligned(data=data, from_grid=from_grid, to_grid=to_grid)

    logger.debug("unaligned grids, slow regridding")
    return regrid_any(data=data, from_grid=from_grid, to_grid=to_grid)


def regrid_aligned(
    data: np.ndarray,
    from_grid: Grid,
    to_grid: Grid,
) -> np.ndarray:
    """
    Re-grids a dataset to a shape defined by to_grid, using a nearest neighbor
    strategy. Values are **not** conserved, so this is mostly useful for masks.
    The source data and the to_grid must share the same projection.
    :param data: 2d gridded data
    :param from_grid: Grid of the source data
    :param to_grid: Target grid to reshape the data to
    :return: 2d dataset of gridded cell values in the target grid
    """
    # grids must have parallel grid lines
    if not to_grid.is_aligned(from_grid):
        raise ValueError("regrid_aligned can only be used between aligned grids")

    # transform to_grid coordinates into from_grid coordinates to
    # efficiently bin them
    grid_transform = pyproj.Transformer.from_crs(crs_from=to_grid.projection.crs, crs_to=from_grid.projection.crs)
    to_grid_x_transformed, to_grid_y_transformed = grid_transform.transform(xx=to_grid.cell_coords_x(), yy=to_grid.cell_coords_y())

    data_np = data if type(data) is np.ndarray else data.to_numpy()

    source_x_indices = np.digitize(to_grid_x_transformed, from_grid.cell_bounds_x()) - 1
    source_y_indices = np.digitize(to_grid_y_transformed, from_grid.cell_bounds_y()) - 1
    xmesh, ymesh = np.meshgrid(source_x_indices, source_y_indices)
    return data_np[ymesh, xmesh]


def regrid_any(
    data: np.ndarray,
    from_grid: Grid,
    to_grid: Grid,
) -> np.ndarray:
    """
    Re-grids a dataset to a shape defined by to_grid, using a nearest neighbor
    strategy. Values are **not** conserved, so this is mostly useful for masks.
    The source data and to_grid can use different projections, but this
    implementation is quite slow. If the grids use the same projection then
    regrid_aligned should be used.
    :param data: 2d gridded data
    :param from_grid: Grid of the source data
    :param to_grid: Target grid to reshape the data to
    :return: 2d dataset of gridded cell values in the target grid
    """
    # when grids dont share a projection, compare individual cells
    regridded_data = np.zeros(to_grid.shape)

    # generate corner points for both grids, in the same crs (lon / lat)
    from_grid_bounds_lon, from_grid_bounds_lat = from_grid.cell_bounds_lonlat()
    to_grid_bounds_lon, to_grid_bounds_lat = to_grid.cell_bounds_lonlat()

    # find a subset of the from_grid that should be examined
    to_grid_bounds = [
        to_grid_bounds_lon.min(), to_grid_bounds_lat.min(),
        to_grid_bounds_lon.max(), to_grid_bounds_lat.max(),
    ]
    # TODO: this may not by a perfect envelope due to curvature
    from_grid_search_space = [
        from_grid.lonlat_to_cell_index(to_grid_bounds[0], to_grid_bounds[1]),
        from_grid.lonlat_to_cell_index(to_grid_bounds[2], to_grid_bounds[3]),
    ]

    for to_grid_iy, to_grid_ix in itertools.product(range(to_grid.shape[0]), range(to_grid.shape[1])):
        to_grid_cell_polygon = geometry.Polygon(zip(to_grid_bounds_lon[to_grid_iy, to_grid_ix], to_grid_bounds_lat[to_grid_iy, to_grid_ix]))

        # search the source grid for the cell with the largest intersection
        largest_intersection = 0
        total_intersection = 0

        for from_grid_iy in range(from_grid_search_space[0][1], from_grid_search_space[1][1]):
            for from_grid_ix in range(from_grid_search_space[0][0], from_grid_search_space[1][0]):

                from_grid_cell_polygon = geometry.Polygon(zip(from_grid_bounds_lon[from_grid_iy, from_grid_ix], from_grid_bounds_lat[from_grid_iy, from_grid_ix]))
                intersection = from_grid_cell_polygon.intersection(to_grid_cell_polygon)

                # cells dont overlap
                if intersection.area <= 0:
                    continue

                # accumulate the sum of the area that has been considered
                total_intersection += intersection.area

                # take the value from the target cell with the largest proportion
                cell_intersection_ratio = intersection.area / to_grid_cell_polygon.area
                if cell_intersection_ratio > largest_intersection:
                    largest_intersection = cell_intersection_ratio
                    regridded_data[to_grid_iy, to_grid_ix] = data[from_grid_iy, from_grid_ix]

                # if we've seen a cell with an intersection larger than the remaining area,
                # we've found the largest intersection
                if largest_intersection > to_grid_cell_polygon.area - total_intersection:
                    break

    return regridded_data
