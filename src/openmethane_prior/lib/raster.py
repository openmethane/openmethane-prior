import numpy as np
import pyproj
import xarray as xr

from openmethane_prior.lib.grid.grid import Grid

# number of input cells to reproject at a time
_BLOCK_CELLS = 2**20

# points transformed along each edge of the target grid to find its extent
# in the input projection
_BBOX_EDGE_POINTS = 100


def remap_raster(
    input_xr: xr.DataArray,
    target_grid: Grid,
    input_crs: pyproj.crs.CRS = 4326,  # EPSG:4362
) -> np.ndarray:
    """
    Maps a rasterio dataset onto the domain grid defined by config.

    If the input dataset uses a non-standard CRS, input coordinates can be
    mapped to the grid by specifying input_crs.

    Returns an np.array in the shape of the domain grid, each cell containing
    the sum of the values of raster cells whose centre point falls within it.
    """
    projection_transformer = pyproj.Transformer.from_crs(
        crs_from=input_crs, crs_to=target_grid.projection.crs, always_xy=True
    )

    # construct a bounding box for the target grid, over the input grid
    # this will limit our search space for mapping input values to target cells.
    # the grid's edges curve in the input projection, so points along each
    # edge are transformed, not just the corners
    target_grid_bounds_x = target_grid.cell_bounds_x()
    target_grid_bounds_y = target_grid.cell_bounds_y()
    input_x_min, input_y_min, input_x_max, input_y_max = projection_transformer.transform_bounds(
        target_grid_bounds_x.min(),
        target_grid_bounds_y.min(),
        target_grid_bounds_x.max(),
        target_grid_bounds_y.max(),
        densify_pts=_BBOX_EDGE_POINTS,
        direction=pyproj.enums.TransformDirection.INVERSE,
    )

    # crop with slices rather than .where(drop=True), which would copy the
    # input as float64 to hold NaNs. raster coordinates are monotonic, so the
    # coordinates inside the box are a contiguous run of indices
    x_inside = np.flatnonzero(
        (input_x_min <= input_xr.x.values) & (input_xr.x.values <= input_x_max)
    )
    y_inside = np.flatnonzero(
        (input_y_min <= input_xr.y.values) & (input_xr.y.values <= input_y_max)
    )
    if x_inside.size == 0 or y_inside.size == 0:
        return np.zeros(target_grid.shape)

    input_search_space = input_xr.isel(
        x=slice(x_inside[0], x_inside[-1] + 1),
        y=slice(y_inside[0], y_inside[-1] + 1),
    ).transpose("y", "x")
    input_search_space_np = input_search_space.to_numpy()
    input_x = input_search_space.x.to_numpy()
    input_y = input_search_space.y.to_numpy()

    # work through blocks of rows, so the coordinates of a dense input never
    # all need to be held in memory at once
    block_rows = max(1, _BLOCK_CELLS // max(1, input_x.size))
    result = np.zeros(target_grid.shape)
    for row_start in range(0, input_y.size, block_rows):
        block = input_search_space_np[row_start : row_start + block_rows]

        # only cells with a value are reprojected: a zero adds nothing to the
        # sum in a target cell, and projecting coordinates is the slow part.
        # this only holds because the result is a sum of input values
        block_iy, block_ix = np.nonzero(block)
        if block_iy.size == 0:
            continue

        # the input cell is counted in the target cell containing its centre
        target_x, target_y = projection_transformer.transform(
            xx=input_x[block_ix], yy=input_y[row_start + block_iy]
        )
        target_ix, target_iy, mask = target_grid.xy_to_cell_index(target_x, target_y)

        # np.add.at accumulates values when target indices repeat. input cells
        # outside the target grid are masked out
        if mask.any():
            np.add.at(
                result,
                (target_iy[mask], target_ix[mask]),
                block[block_iy[mask], block_ix[mask]],
            )

    return result
