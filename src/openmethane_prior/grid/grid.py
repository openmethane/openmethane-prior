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

from typing import Any

import numpy as np
import pyproj

class Grid:
    """
    Grid details and utilities for working with grid coordinates.
    """

    dimensions: tuple[int, int]
    """Number of grid cells along the (x, y) axes"""

    shape: tuple[int, int]
    """Number of grid cells along the (y, x) axes.
    Useful for xarray dimensions ordered (y, x)."""

    origin_xy: tuple[float, float]
    """Location of grid origin, sometimes called LLC or 'lower left corner'"""

    cell_size: tuple[float, float]
    """Dimensions of a grid cell in grid projection coordinates"""

    cell_area: float
    """Area of a single grid cell in grid projection coordinate units."""

    llc_center_xy: tuple[float, float]
    """Coordinates for the center point of the lower left corner (0, 0) grid
    cell in grid projection coordinates."""

    projection: pyproj.Proj
    """Parameters for constructing a pyproj.Proj for the grid"""

    def __init__(
        self,
        dimensions: tuple[int, int],
        origin_xy: tuple[float, float],
        cell_size: tuple[float, float],
        proj_params: Any = "EPSG:4326", # default projection
    ):
        self.dimensions = dimensions
        self.origin_xy = origin_xy
        self.cell_size = cell_size
        self.proj_params = proj_params

        self.projection = pyproj.Proj(self.proj_params)

        # derived properties
        self.shape = (dimensions[1], dimensions[0])
        self.llc_center_xy = (
            self.origin_xy[0] + (self.cell_size[0] / 2),
            self.origin_xy[1] + (self.cell_size[1] / 2)
        )
        self.cell_area = self.cell_size[0] * self.cell_size[1]


    def __eq__(self, other):
        return (
            self.dimensions == other.dimensions
            and self.origin_xy == other.origin_xy
            and self.llc_center_xy == other.llc_center_xy
            and self.cell_size == other.cell_size
            and self.projection.is_exact_same(other.projection)
        )

    def is_aligned(self, other):
        if self == other or self.projection.is_exact_same(other.projection):
            return True

        # can't be aligned if the projection type is different
        if self.projection.name != other.projection.name:
            return False

        # lambert projections are aligned if parameters are the same, ignoring x/y offset
        if self.projection.name == "lcc":
            self_srs_parts = [part for part in self.projection.srs.split(" ") if not (part.startswith("+x_0") or part.startswith("+y_0"))]
            other_srs_parts = [part for part in other.projection.srs.split(" ") if not (part.startswith("+x_0") or part.startswith("+y_0"))]
            return " ".join(self_srs_parts) == " ".join(other_srs_parts)

        raise NotImplementedError("non-lambert projections comparisons are not implemented")

    def lonlat_to_xy(self, lon, lat) -> tuple[float, float]:
        return self.projection.transform(xx=lon, yy=lat, direction=pyproj.enums.TransformDirection.FORWARD)

    def xy_to_lonlat(self, x, y) -> tuple[float, float]:
        return self.projection.transform(xx=x, yy=y, direction=pyproj.enums.TransformDirection.INVERSE)

    def cell_coords_x(self) -> np.ndarray[int, np.float64]:
        """
        Cell center coordinates for every grid cell along the x axis, in grid
        projection coordinates.
        """
        return self.llc_center_xy[0] + np.arange(self.dimensions[0]) * self.cell_size[0]

    def cell_coords_y(self) -> np.ndarray[int, np.float64]:
        """
        Cell center coordinates for every grid cell along the y axis, in grid
        projection coordinates.
        """
        return self.llc_center_xy[1] + np.arange(self.dimensions[1]) * self.cell_size[1]

    def cell_bounds_x(self) -> np.ndarray[int, np.float64]:
        """
        Boundary coordinates for the edges of every grid cell along the x axis,
        in grid projection coordinates.
        The size of the return array is always one larger than the number of
        grid cells, with the bounds of the first cell in bounds[0], bounds[1],
        and the bounds of the last cell as bounds[n], bounds[n + 1].
        """
        return self.origin_xy[0] + np.arange(self.dimensions[0] + 1) * self.cell_size[0]

    def cell_bounds_y(self) -> np.ndarray[int, np.float64]:
        """
        Boundary coordinates for the edges of every grid cell along the y axis,
        in grid projection coordinates.
        The size of the return array is always one larger than the number of
        grid cells, with the bounds of the first cell in bounds[0], bounds[1],
        and the bounds of the last cell as bounds[n], bounds[n + 1].
        """
        return self.origin_xy[1] + np.arange(self.dimensions[1] + 1) * self.cell_size[1]

    def cell_bounds_lonlat(self) -> tuple[np.ndarray, np.ndarray]:
        bounds_x = self.cell_bounds_x()
        bounds_y = self.cell_bounds_y()

        # return values in the shape of the grid, with 4 corners for each cell
        lon_bounds = np.ndarray(shape=(self.shape[0], self.shape[1], 4), dtype=np.float64)
        lat_bounds = np.ndarray(shape=(self.shape[0], self.shape[1], 4), dtype=np.float64)

        for iy in range(self.shape[0]):
            for ix in range(self.shape[1]):
                cell_bounds_x = [bounds_x[ix], bounds_x[ix + 1], bounds_x[ix + 1], bounds_x[ix]]
                cell_bounds_y = [bounds_y[iy], bounds_y[iy], bounds_y[iy + 1], bounds_y[iy + 1]]
                cell_bounds_lon, cell_bounds_lat = self.xy_to_lonlat(cell_bounds_x, cell_bounds_y)
                lon_bounds[iy, ix] = cell_bounds_lon
                lat_bounds[iy, ix] = cell_bounds_lat

        return lon_bounds, lat_bounds


    def valid_cell_coords(self, coord_x: Any, coord_y: Any) -> Any:
        """
        Return true if the grid cell coords refer to a valid cell in the grid.
        """
        return (
            (coord_x >= 0) & (coord_x < self.dimensions[0]) &
            (coord_y >= 0) & (coord_y < self.dimensions[1])
        )

    def xy_to_cell_index(self, x: Any, y: Any) -> tuple[Any, Any, Any]:
        """
        Find the grid cell indices for the cells containing each provided
        grid projection coordinate. Return tuple also includes a binary mask
        representing if coords are valid and inside the grid extent.
        """
        # calculate indices assuming regular grid
        cell_index_x = np.floor((x - self.origin_xy[0]) / self.cell_size[0]).astype('int')
        cell_index_y = np.floor((y - self.origin_xy[1]) / self.cell_size[1]).astype('int')

        # determine which coords are within the grid
        mask = self.valid_cell_coords(cell_index_x, cell_index_y)

        return cell_index_x, cell_index_y, mask

    def lonlat_to_cell_index(self, lon: Any, lat: Any) -> tuple[Any, Any, Any]:
        """
        Find the grid cell indices for the cells containing each provided
        lon/lat coordinate. Return tuple also includes a binary mask in the
        third position for whether coords are valid and inside the grid extent.
        """
        x, y = self.lonlat_to_xy(lon=lon, lat=lat)

        return self.xy_to_cell_index(x, y)
