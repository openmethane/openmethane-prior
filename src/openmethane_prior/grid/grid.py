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

    center_lonlat: tuple[float, float]
    """Grid center point in longitude and latitude coordinates"""

    center_xy: tuple[float, float]
    """Grid center point in grid projection coordinates"""

    origin_xy: tuple[float, float]
    """Location of grid origin relative to center_lonlat"""

    cell_size: tuple[float, float]
    """Dimensions of a grid cell in grid projection coordinates"""

    cell_area: float
    """Area of a single grid cell in grid projection coordinate units."""

    llc_xy: tuple[float, float]
    """Lower left corner coordinates in grid projection coordinates. The
    lower boundary in both x and y dimensions."""

    llc_center_xy: tuple[float, float]
    """Coordinates for the center point of the lower left corner (0, 0) grid
    cell in grid projection coordinates."""

    projection: pyproj.Proj
    """Parameters for constructing a pyproj.Proj for the grid"""

    def __init__(
        self,
        dimensions: tuple[int, int],
        center_lonlat: tuple[float, float],
        origin_xy: tuple[float, float],
        cell_size: tuple[float, float],
        proj_params: Any = "EPSG:4326", # default projection
    ):
        self.dimensions = dimensions
        self.center_lonlat = center_lonlat
        self.origin_xy = origin_xy
        self.cell_size = cell_size
        self.proj_params = proj_params

        self.projection = pyproj.Proj(self.proj_params)

        # derived properties
        self.shape = (dimensions[1], dimensions[0])
        self.center_xy = self.lonlat_to_xy(lon=self.center_lonlat[0], lat=self.center_lonlat[1])
        self.llc_xy = (
            self.center_xy[0] + self.origin_xy[0],
            self.center_xy[1] + self.origin_xy[1]
        )
        self.llc_center_xy = (
            self.llc_xy[0] + (self.cell_size[0] / 2),
            self.llc_xy[1] + (self.cell_size[1] / 2)
        )
        self.cell_area = self.cell_size[0] * self.cell_size[1]


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
        return self.llc_xy[0] + np.arange(self.dimensions[0] + 1) * self.cell_size[0]

    def cell_bounds_y(self) -> np.ndarray[int, np.float64]:
        """
        Boundary coordinates for the edges of every grid cell along the y axis,
        in grid projection coordinates.
        The size of the return array is always one larger than the number of
        grid cells, with the bounds of the first cell in bounds[0], bounds[1],
        and the bounds of the last cell as bounds[n], bounds[n + 1].
        """
        return self.llc_xy[1] + np.arange(self.dimensions[1] + 1) * self.cell_size[1]

    def valid_cell_coords(self, coord_x: int, coord_y: int) -> bool:
        """
        Return true if the grid cell coords refer to a valid cell in the grid.
        """
        return (
            (coord_x >= 0) & (coord_x < self.dimensions[0]) &
            (coord_y >= 0) & (coord_y < self.dimensions[1])
        )

    def lonlat_to_cell_index(self, lon: Any, lat: Any) -> tuple[Any, Any, Any]:
        """
        Find the grid cell indices for the cells containing each provided
        lon/lat coordinate. Return tuple also includes a binary mask in the
        third position for whether coords are valid and inside the grid extent.
        """
        x, y = self.lonlat_to_xy(lon=lon, lat=lat)

        # calculate indices assuming regular grid
        cell_index_x = np.floor((x - self.llc_xy[0]) / self.cell_size[0]).astype('int')
        cell_index_y = np.floor((y - self.llc_xy[1]) / self.cell_size[1]).astype('int')

        # determine which coords are within the grid
        mask = self.valid_cell_coords(cell_index_x, cell_index_y)

        return cell_index_x, cell_index_y, mask
