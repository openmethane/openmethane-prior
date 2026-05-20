import numpy as np
import pytest
from shapely.geometry import MultiPolygon, Polygon

from openmethane_prior.lib.grid.geometry import grid_mask_from_polygon
from openmethane_prior.lib.grid.grid import Grid


# 4x4 grid, cell centers at x=[0.5, 1.5, 2.5, 3.5], y=[0.5, 1.5, 2.5, 3.5]
# Default projection (EPSG:4326) so grid coordinates == lon/lat degrees
@pytest.fixture
def small_grid():
    return Grid(dimensions=(4, 4), origin_xy=(0, 0), cell_size=(1, 1))


def test_polygon_covers_inner_cells(small_grid):
    # Polygon from (1,1) to (3,3) covers only the 4 inner cell centres
    polygon = Polygon([(1, 1), (3, 1), (3, 3), (1, 3)])
    mask = grid_mask_from_polygon(small_grid, polygon)

    assert mask.shape == small_grid.shape
    np.testing.assert_array_equal(mask, [
        [False, False, False, False],
        [False, True,  True,  False],
        [False, True,  True,  False],
        [False, False, False, False],
    ])


def test_polygon_covers_full_grid(small_grid):
    polygon = Polygon([(-1, -1), (5, -1), (5, 5), (-1, 5)])
    mask = grid_mask_from_polygon(small_grid, polygon)

    np.testing.assert_array_equal(mask, np.ones(small_grid.shape, dtype=bool))


def test_polygon_outside_grid_returns_all_false(small_grid):
    polygon = Polygon([(10, 10), (20, 10), (20, 20), (10, 20)])
    mask = grid_mask_from_polygon(small_grid, polygon)

    np.testing.assert_array_equal(mask, np.zeros(small_grid.shape, dtype=bool))


def test_multipolygon_covers_two_separate_regions(small_grid):
    # Two non-adjacent 1x1 squares: bottom-left and top-right corners
    poly_a = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])  # centre (0.5, 0.5)
    poly_b = Polygon([(3, 3), (4, 3), (4, 4), (3, 4)])  # centre (3.5, 3.5)
    multi = MultiPolygon([poly_a, poly_b])

    mask = grid_mask_from_polygon(small_grid, multi)

    np.testing.assert_array_equal(mask, [
        [True,  False, False, False],
        [False, False, False, False],
        [False, False, False, False],
        [False, False, False, True ],
    ])


def test_mask_shape_matches_grid_shape():
    grid = Grid(dimensions=(10, 5), origin_xy=(0, 0), cell_size=(1, 1))
    polygon = Polygon([(2, 1), (8, 1), (8, 4), (2, 4)])
    mask = grid_mask_from_polygon(grid, polygon)

    assert mask.shape == grid.shape  # (ny=5, nx=10)
    assert mask.dtype == bool