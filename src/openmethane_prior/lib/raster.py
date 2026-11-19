import numpy as np
import pyproj
import xarray as xr

from openmethane_prior.lib.grid.grid import Grid


def remap_raster(
    input_xr: xr.DataArray,
    target_grid: Grid,
    input_crs: pyproj.crs.CRS = 4326, # EPSG:4362
) -> np.ndarray:
    """
    Maps a rasterio dataset onto the domain grid defined by config.

    If the input dataset uses a non-standard CRS, input coordinates can be
    mapped to the grid by specifying input_crs.

    Returns an np.array in the shape of the domain grid, each cell containing
    the aggregate of raster values who's center point fell within the cell.
    """
    projection_transformer = pyproj.Transformer.from_crs(crs_from=input_crs, crs_to=target_grid.projection.crs, always_xy=True)

    # construct a bounding box for the target grid, over the input grid
    # this will limit our search space for mapping input values to target cells
    target_grid_bounds_x = target_grid.cell_bounds_x()
    target_grid_bounds_y = target_grid.cell_bounds_y()
    target_grid_x_min, target_grid_x_max = target_grid_bounds_x.min(), target_grid_bounds_x.max()
    target_grid_y_min, target_grid_y_max = target_grid_bounds_y.min(), target_grid_bounds_y.max()
    target_bbox_input_x, target_bbox_input_y = projection_transformer.transform(
        xx=np.array([target_grid_x_min, target_grid_x_max, target_grid_x_max, target_grid_x_min]),
        yy=np.array([target_grid_y_min, target_grid_y_min, target_grid_y_max, target_grid_y_max]),
        direction=pyproj.enums.TransformDirection.INVERSE,
    )

    # crop with slices rather than .where(drop=True), which would copy the
    # input as float64 to hold NaNs. raster coordinates are monotonic, so the
    # coordinates inside the box are a contiguous run of indices
    x_inside = np.flatnonzero(
        (target_bbox_input_x.min() <= input_xr.x.values) &
        (input_xr.x.values <= target_bbox_input_x.max())
    )
    y_inside = np.flatnonzero(
        (target_bbox_input_y.min() <= input_xr.y.values) &
        (input_xr.y.values <= target_bbox_input_y.max())
    )
    if x_inside.size == 0 or y_inside.size == 0:
        return np.zeros(target_grid.shape)

    input_search_space = input_xr.isel(
        x=slice(x_inside[0], x_inside[-1] + 1),
        y=slice(y_inside[0], y_inside[-1] + 1),
    ).transpose("y", "x")
    input_search_space_np = input_search_space.to_numpy()

    # the raster is defined lat-lon so we need to reproject each row separately onto the LCC grid
    result = np.zeros(target_grid.shape)
    for iy in range(input_search_space.y.size):
        y = input_search_space.y.item(iy)
        # proj needs x,y coords in equal-sized lists, each point in the row
        # will have the same y coord
        y_row = np.array([y]).repeat(input_search_space.x.size)

        # the central point in the high-res raster cell lies inside the cell
        # defined on the domain grid
        target_x, target_y = projection_transformer.transform(xx=input_search_space.x, yy=y_row)
        target_ix, target_iy, mask = target_grid.xy_to_cell_index(target_x, target_y)

        # input domain is bigger so mask indices out of range
        if mask.any():
            # we accumulate values from each high-res grid in the raster onto
            # our domain.
            # the following needs to use .at method since target_iy,target_ix indices may be repeated and we need to acumulate
            np.add.at(result, (target_iy[mask], target_ix[mask]), input_search_space_np[iy, mask])

    return result
