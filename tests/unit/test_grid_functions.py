import pytest
import xarray as xr

from openmethane_prior.utils import extract_bounds

def test_extract_bounds():
    # a single dimension of a 3x3 grid, represented by 4x4 matrix containing
    # grid cell edge coords
    corner_values = xr.DataArray(
        data=[
            [0, 1, 2, 3],
            [4, 5, 6, 7],
            [8, 9, 10, 11],
            [12, 13, 14, 15],
        ],
        coords={
            "y": range(4),
            "x": range(4),
        }
    )

    bounds = extract_bounds(corner_values)

    # 3x3 grid, 4 corners per cell
    assert bounds.shape == (3, 3, 4)

    # in this example, assuming our DataArray holds x coordinates with
    # 0,0 in the bottom left, the coordinates for the grid cell at 0,0
    # would be:
    # (4, y2) (5, y3)
    # (0, y0) (1, y1)
    # cell corners are constructed clockwise from bottom left
    assert list(bounds[0][0].values) == [0, 1, 5, 4]
    assert list(bounds[0][1].values) == [1, 2, 6, 5]
    assert list(bounds[0][2].values) == [2, 3, 7, 6]
    assert list(bounds[2][2].values) == [10, 11, 15, 14]

    # see https://cfconventions.org/Data/cf-conventions/cf-conventions-1.11/cf-conventions.html#cell-boundaries
