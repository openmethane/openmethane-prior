
import xarray as xr

from .grid import Grid

class DomainGrid(Grid):
    """
    Grid details and utilities for working with grid coordinates.
    """
    def __init__(self, domain_ds: xr.Dataset):
        # if the domain was generated from WRF geometry, we must use a
        # spherical Earth in our projection.
        # https://fabienmaussion.info/2018/01/06/wrf-projection/
        # TODO: allow these params to be specified for non-WRF domains
        earth_equatorial_axis_radius = 6370000
        earth_polar_axis_radius = 6370000
        proj_params = dict(
            proj="lcc",
            lat_1=domain_ds.TRUELAT1,
            lat_2=domain_ds.TRUELAT2,
            lat_0=domain_ds.MOAD_CEN_LAT,
            lon_0=domain_ds.STAND_LON,
            # semi-major or equatorial axis radius
            a=earth_equatorial_axis_radius,
            # semi-minor, or polar axis radius
            b=earth_polar_axis_radius,
        )

        super(DomainGrid, self).__init__(
            dimensions=(domain_ds.COL.size, domain_ds.ROW.size),
            center_lonlat=(domain_ds.XCENT, domain_ds.YCENT),
            origin_xy=(domain_ds.XORIG, domain_ds.YORIG),
            cell_size=(domain_ds.XCELL, domain_ds.YCELL),
            proj_params=proj_params,
        )
