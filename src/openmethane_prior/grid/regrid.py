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
    Re-grids a dataset to a shape defined by to_grid, using a nearest neighbor
    strategy. Values are **not** conserved, so this is mostly useful for masks.
    The source data and the to_grid must share the same projection.
    :param data: 2d gridded data
    :param from_grid: Grid of the source data
    :param to_grid: Target grid to reshape the data to
    :return: 2d dataset of gridded cell values in the target grid
    """
    data_np = data if type(data) is np.ndarray else data.to_numpy()

    source_x_indices = np.digitize(to_grid.cell_coords_x(), from_grid.cell_bounds_x()) - 1
    source_y_indices = np.digitize(to_grid.cell_coords_y(), from_grid.cell_bounds_y()) - 1
    xmesh, ymesh = np.meshgrid(source_x_indices, source_y_indices)
    return data_np[ymesh, xmesh]
