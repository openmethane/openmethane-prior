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


def test_regrid_data_different_projections():
    source_grid = Grid(
        dimensions=(8, 8),
        origin_xy=(-137.38, -38.51), # GDA2020 center is 133.38,-34.51
        cell_size=(1, 1),
    )
    target_grid = Grid(
        dimensions=(8, 8),
        origin_xy=(-137, -38), # not exactly aligned with source_grid
        cell_size=(1, 1),
        proj_params="EPSG:7843" # GDA2020 in degrees
    )
    data = np.zeros(source_grid.shape, dtype=np.float64)
    data[2, 2] = 1 # allocate a single pixel with a 1 in the source grid

    result = regrid_data(data, from_grid=source_grid, to_grid=target_grid)

    assert result.shape == target_grid.shape
    assert result.sum() == 1 # cells are the same size, so 1 value only appears once
    assert result[1, 2].sum() == 1 # result is not at 2,2 because grids aren't aligned


def test_regrid_data_different_projections_sizes():
    source_grid = Grid(
        dimensions=(8, 8),
        origin_xy=(-137.38, -38.51), # GDA2020 center is 133.38,-34.51
        cell_size=(2, 2),
    )
    target_grid = Grid(
        dimensions=(8, 8),
        origin_xy=(-137, -38), # not exactly aligned with source_grid
        cell_size=(1, 1), # smaller grid
        proj_params="EPSG:7843" # GDA2020 in degrees
    )
    data = np.zeros(source_grid.shape, dtype=np.float64)
    data[2, 2] = 1 # allocate a single pixel with a 1 in the source grid

    result = regrid_data(data, from_grid=source_grid, to_grid=target_grid)

    assert result.shape == target_grid.shape
    assert result.sum() == 4 # cells are the 1:4, so 1 value appears 4 times
    assert result[3:5, 4:6].sum() == 4 # result is spread from 3,4 to 4,5
