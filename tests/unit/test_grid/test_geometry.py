import numpy as np
import pytest
from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon

from openmethane_prior.lib.grid.geometry import grid_mask_from_polygon, grid_weights_from_linestring
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


# ---------------------------------------------------------------------------
# grid_weights_from_linestring
# ---------------------------------------------------------------------------

# Reuse the same 4x4 grid. Cell centres at x=[0.5,1.5,2.5,3.5],
# y=[0.5,1.5,2.5,3.5]; cell bounds at integer coordinates 0..4.


def test_linestring_weights_shape_and_dtype(small_grid):
    line = LineString([(0, 0.5), (4, 0.5)])
    weights = grid_weights_from_linestring(small_grid, line)

    assert weights.shape == small_grid.shape  # (ny=4, nx=4)
    assert weights.dtype == np.float64


def test_linestring_horizontal_full_row(small_grid):
    # Horizontal line at y=0.5 crossing all four cells in row 0.
    # Each cell gets length 1 out of total length 4 → weight 0.25.
    line = LineString([(0, 0.5), (4, 0.5)])
    weights = grid_weights_from_linestring(small_grid, line)

    np.testing.assert_allclose(weights, [
        [0.25, 0.25, 0.25, 0.25],
        [0.0,  0.0,  0.0,  0.0 ],
        [0.0,  0.0,  0.0,  0.0 ],
        [0.0,  0.0,  0.0,  0.0 ],
    ])


def test_linestring_vertical_full_column(small_grid):
    # Vertical line at x=0.5 crossing all four cells in column 0.
    line = LineString([(0.5, 0), (0.5, 4)])
    weights = grid_weights_from_linestring(small_grid, line)

    np.testing.assert_allclose(weights, [
        [0.25, 0.0, 0.0, 0.0],
        [0.25, 0.0, 0.0, 0.0],
        [0.25, 0.0, 0.0, 0.0],
        [0.25, 0.0, 0.0, 0.0],
    ])


def test_linestring_diagonal(small_grid):
    # 45-degree diagonal from (0,0) to (4,4). Passes through one cell per row
    # on the main diagonal; each cell clip has length √2 out of total 4√2.
    line = LineString([(0, 0), (4, 4)])
    weights = grid_weights_from_linestring(small_grid, line)

    np.testing.assert_allclose(weights, [
        [0.25, 0.0,  0.0,  0.0 ],
        [0.0,  0.25, 0.0,  0.0 ],
        [0.0,  0.0,  0.25, 0.0 ],
        [0.0,  0.0,  0.0,  0.25],
    ])


def test_linestring_unequal_cell_lengths(small_grid):
    # Line from (0.5, 0.5) to (2.5, 0.5): total length 2.
    # Passes through cell (0,0) for 0.5, cell (1,0) for 1.0, cell (2,0) for 0.5.
    line = LineString([(0.5, 0.5), (2.5, 0.5)])
    weights = grid_weights_from_linestring(small_grid, line)

    np.testing.assert_allclose(weights[0], [0.25, 0.5, 0.25, 0.0])
    np.testing.assert_allclose(weights[1:], 0.0)


def test_linestring_weights_sum_to_one_when_inside(small_grid):
    line = LineString([(0.3, 0.7), (3.8, 2.1)])
    weights = grid_weights_from_linestring(small_grid, line)

    np.testing.assert_allclose(weights.sum(), 1.0)


def test_linestring_outside_grid_returns_zeros(small_grid):
    line = LineString([(10, 10), (20, 10)])
    weights = grid_weights_from_linestring(small_grid, line)

    np.testing.assert_array_equal(weights, np.zeros(small_grid.shape))


def test_linestring_partial_outside_grid(small_grid):
    # Line from x=-1 to x=2 at y=0.5; 1 unit is outside, 2 units are inside.
    # Weights should sum to 2/3 of total length 3.
    line = LineString([(-1, 0.5), (2, 0.5)])
    weights = grid_weights_from_linestring(small_grid, line)

    np.testing.assert_allclose(weights.sum(), 2 / 3)
    # Only cells (0,0) and (1,0) should be non-zero, each with weight 1/3
    np.testing.assert_allclose(weights[0, :2], [1 / 3, 1 / 3])
    np.testing.assert_allclose(weights[0, 2:], 0.0)
    np.testing.assert_allclose(weights[1:], 0.0)


def test_linestring_zero_length_returns_zeros(small_grid):
    # Degenerate line (single point) must not raise ZeroDivisionError.
    line = LineString([(1.5, 1.5), (1.5, 1.5)])
    weights = grid_weights_from_linestring(small_grid, line)

    np.testing.assert_array_equal(weights, np.zeros(small_grid.shape))


def test_multilinestring_two_segments(small_grid):
    # Two equal-length segments in different cells.
    # Segment A: (0,0.5)→(1,0.5), length 1 in cell (0,0)
    # Segment B: (2,0.5)→(3,0.5), length 1 in cell (2,0)
    # Total length 2 → weight 0.5 per segment, 0.5 per cell.
    multi = MultiLineString([
        [(0, 0.5), (1, 0.5)],
        [(2, 0.5), (3, 0.5)],
    ])
    weights = grid_weights_from_linestring(small_grid, multi)

    np.testing.assert_allclose(weights[0], [0.5, 0.0, 0.5, 0.0])
    np.testing.assert_allclose(weights[1:], 0.0)


def test_multilinestring_weights_sum_to_one_when_inside(small_grid):
    multi = MultiLineString([
        [(0.1, 0.5), (1.9, 0.5)],
        [(0.5, 1.5), (0.5, 3.5)],
    ])
    weights = grid_weights_from_linestring(small_grid, multi)

    np.testing.assert_allclose(weights.sum(), 1.0)


def test_linestring_non_unit_cell_size():
    # Grid with 2x2 km cells to confirm cell_size scaling is handled correctly.
    grid = Grid(dimensions=(3, 3), origin_xy=(0, 0), cell_size=(2, 2))
    # Horizontal line at y=1 across all three columns; total length 6.
    line = LineString([(0, 1), (6, 1)])
    weights = grid_weights_from_linestring(grid, line)

    np.testing.assert_allclose(weights.sum(), 1.0)
    np.testing.assert_allclose(weights[0], [1 / 3, 1 / 3, 1 / 3])
