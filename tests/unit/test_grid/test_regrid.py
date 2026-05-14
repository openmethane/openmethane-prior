import numpy as np

from openmethane_prior.lib.grid.grid import Grid
from openmethane_prior.lib.grid.regrid import regrid_data


def test_regrid_data_same_grid():
    source_grid = Grid(
        dimensions=(8, 10),
        origin_xy=(-4, -5),
        cell_size=(1, 2),
    )
    target_grid = Grid(
        dimensions=(8, 10),
        origin_xy=(-4, -5),
        cell_size=(1, 2),
    )
    data = np.ones(source_grid.shape, dtype=np.float64)

    result = regrid_data(data, from_grid=source_grid, to_grid=target_grid)

    assert result.shape == target_grid.shape
    assert result[0, 0] == 1.0
    assert result.sum() == result.shape[0] * result.shape[1]


def test_regrid_data_smaller_grid():
    source_grid = Grid(
        dimensions=(8, 6),
        origin_xy=(-8, -9),
        cell_size=(2, 3),
    )
    target_grid = Grid(
        dimensions=(4, 6),
        origin_xy=(-5, -5),
        cell_size=(1, 1), # cells are smaller source grid
    )
    data = np.zeros(source_grid.shape, dtype=np.float64)
    data[2, 2] = 1 # allocate a single pixel with a 1 in the source grid

    result = regrid_data(data, from_grid=source_grid, to_grid=target_grid)

    assert result.shape == target_grid.shape
    assert result.sum() == 2 * 3 # source cells are 6x larger, so we should see 6 values of 1
    assert result[2:5, 1:4].sum() == 2 * 3 # cluster of 1s is at 1,2 in the smaller grid


def test_regrid_data_different_projections_raises():
    source_grid = Grid(
        dimensions=(8, 8),
        origin_xy=(-137.38, -38.51),
        cell_size=(1, 1),
    )
    target_grid = Grid(
        dimensions=(8, 8),
        origin_xy=(-137, -38),
        cell_size=(1, 1),
        proj_params="EPSG:7843"
    )
    data = np.zeros(source_grid.shape, dtype=np.float64)

    import pytest
    with pytest.raises(ValueError, match="regrid_data_array_conservative"):
        regrid_data(data, from_grid=source_grid, to_grid=target_grid)
