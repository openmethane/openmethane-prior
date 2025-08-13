import numpy as np

from openmethane_prior.grid.grid import Grid
from openmethane_prior.grid.regrid import regrid_aligned


def test_regrid_aligned_same_grid():
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

    result = regrid_aligned(data, source_grid, target_grid)

    assert result.shape == target_grid.shape
    assert result[0, 0] == 1.0
    assert result.sum() == result.shape[0] * result.shape[1]

def test_regrid_aligned_smaller_grid():
    source_grid = Grid(
        dimensions=(8, 10),
        origin_xy=(-4, -5),
        cell_size=(1, 2),
    )
    target_grid = Grid(
        dimensions=(4, 5),
        origin_xy=(-2, -3),
        cell_size=(1, 1), # cells are half the area of source grid
    )
    data = np.ones(source_grid.shape, dtype=np.float64)

    result = regrid_aligned(data, source_grid, target_grid)

    assert result.shape == target_grid.shape
    assert target_grid.cell_area / source_grid.cell_area == 0.5
    np.testing.assert_almost_equal(result[0, 0], target_grid.cell_area / source_grid.cell_area)
    assert result.sum() == result.shape[0] * result.shape[1] * 0.5
