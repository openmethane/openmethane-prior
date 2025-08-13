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

from .grid import Grid


def regrid_aligned(
    data: np.array,
    from_grid: Grid,
    to_grid: Grid,
) -> np.array:
    """
    Re-grids and subsets a dataset to a shape defined by to_grid. The source
    data and the to_grid must share the same projection.
    :param data: 2d gridded data
    :param from_grid: Grid of the source data
    :param to_grid: Target grid to reshape the data to
    :return: 2d dataset of gridded cell values in the target grid
    """
    regridded_data = np.zeros(to_grid.shape, dtype=data.dtype)
    target_cell_ratio = to_grid.cell_area / from_grid.cell_area
    target_coords_x = to_grid.cell_coords_x()
    target_coords_y = to_grid.cell_coords_y()

    for iy, ix in itertools.product(range(regridded_data.shape[0]), range(regridded_data.shape[1])):
        # find the cell indexes for each target cell in the source data grid
        source_ix, source_iy, source_mask = from_grid.xy_to_cell_index(target_coords_x[ix], target_coords_y[iy])

        if source_mask:
            regridded_data[iy, ix] = data[source_iy, source_ix] * target_cell_ratio

    return regridded_data
