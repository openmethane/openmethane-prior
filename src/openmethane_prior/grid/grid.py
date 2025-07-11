import math

import numpy as np
import pyproj
import xarray as xr

class Grid:
    """
    Grid details and utilities for working with grid coordinates.
    """

    domain_ds: xr.Dataset
    """Source for grid attributes"""

    dimensions: tuple[int, int]
    """Number of grid cells along the x and y axis"""

    center_lonlat: tuple[float, float]
    """Grid center point in longitude and latitude coordinates"""

    origin_xy: tuple[float, float]
    """Location of grid origin relative to center_lonlat"""

    cell_size: tuple[float, float]
    """Dimensions of a grid cell in grid projection coordinates"""

    def __init__(self, domain_ds: xr.Dataset):
        self.domain_ds = domain_ds

        self.dimensions = (self.domain_ds.COL.size, self.domain_ds.ROW.size)
        self.center_lonlat = (self.domain_ds.XCENT, self.domain_ds.YCENT)
        self.origin_xy = (self.domain_ds.XORIG, self.domain_ds.YORIG)
        self.cell_size = (self.domain_ds.XCELL, self.domain_ds.YCELL)

    @property
    def shape(self) -> tuple[int, int]:
        """
        Shape of the grid, with y-axis in first position. This is useful when
        establishing xarray dimensions, which are often ordered (y, x).
        """
        return (self.dimensions[1], self.dimensions[0])

    @property
    def projection(self) -> pyproj.Proj:
        """
        Projection used to convert between lon/lat coordinates and grid
        projection coordinates.
        """
        # if the domain was generated from WRF geometry, we must use a
        # spherical Earth in our projection.
        # https://fabienmaussion.info/2018/01/06/wrf-projection/
        # TODO: allow these params to be specified for non-WRF domains
        earth_equatorial_axis_radius = 6370000
        earth_polar_axis_radius = 6370000

        return pyproj.Proj(
            proj="lcc",
            lat_1=self.domain_ds.TRUELAT1,
            lat_2=self.domain_ds.TRUELAT2,
            lat_0=self.domain_ds.MOAD_CEN_LAT,
            lon_0=self.domain_ds.STAND_LON,
            # semi-major or equatorial axis radius
            a=earth_equatorial_axis_radius,
            # semi-minor, or polar axis radius
            b=earth_polar_axis_radius,
        )

    def lonlat_to_xy(self, lon, lat) -> tuple[float, float]:
        return self.projection.transform(xx=lon, yy=lat, direction=pyproj.enums.TransformDirection.FORWARD)

    def xy_to_lonlat(self, x, y) -> tuple[float, float]:
        return self.projection.transform(xx=x, yy=y, direction=pyproj.enums.TransformDirection.INVERSE)

    @property
    def center_xy(self) -> tuple[float, float]:
        """
        Grid center point in grid projection coordinates, with respect to the
        projection center point. This is not always (0,0), particularly in
        subdomains.
        """
        return self.lonlat_to_xy(lon=self.center_lonlat[0], lat=self.center_lonlat[1])

    @property
    def llc_xy(self) -> tuple[float, float]:
        """
        Lower left corner coordinates in grid projection coordinates. This is
        the extreme lower boundary (sometimes refered to as the grid origin) in
        both x and y dimensions.
        """
        return (
            self.center_xy[0] + self.origin_xy[0],
            self.center_xy[1] + self.origin_xy[1]
        )

    @property
    def llc_center_xy(self) -> tuple[float, float]:
        """
        Coordinates for the center point of the lower left corner grid cell
        in grid projection coordinates. This would be the center point of the
        grid cell at (0, 0) in grid cell coordinates.
        """
        return (
            self.llc_xy[0] + (self.cell_size[0] / 2),
            self.llc_xy[1] + (self.cell_size[1] / 2)
        )

    @property
    def cell_area(self) -> float:
        """
        Area of a single grid cell in grid projection coordinate units.
        """
        return self.cell_size[0] * self.cell_size[1]

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

    def valid_cell_coords(self, coords: tuple[int, int]) -> bool:
        """
        Return true if the grid cell coords refer to a valid cell in the grid.
        """
        return (
            coords[0] >= 0 and coords[0] < self.dimensions[0] and
            coords[1] >= 0 and coords[1] < self.dimensions[1]
        )

    def find_cell(
        self,
        xy: tuple[float, float] | None = None,
        lonlat: tuple[float, float] | None = None,
    ) -> tuple[int, int] | None:
        """
        Return the grid cell coordinates for the cell which contains the
        point provided in xy or lonlat arguments.
        :param xy: Search point in grid projection coordinates.
        :param lonlat: Search point in longitude / latitude coordinates.
        :return: Grid cell coordinates or None if coords are not in the grid
        """
        if xy is None and lonlat is None:
            raise ValueError("find_cell: xy or lonlat must be provided")
        if xy is not None and lonlat is not None:
            raise ValueError("find_cell: provide only one of xy or lonlat")

        search_xy = xy if xy is not None else self.lonlat_to_xy(*lonlat)

        grid_coords = (
            math.floor((search_xy[0] - self.llc_xy[0]) / self.cell_size[0]),
            math.floor((search_xy[1] - self.llc_xy[1]) / self.cell_size[1])
        )
        return grid_coords if self.valid_cell_coords(grid_coords) else None
