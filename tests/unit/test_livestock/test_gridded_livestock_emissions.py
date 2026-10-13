import numpy as np

from openmethane_prior.lib.grid.grid import Grid
from openmethane_prior.sectors.livestock.sector import (
    gridded_livestock_emissions,
)

# Simple 5x5 degree grid using default EPSG:4326 projection (lon/lat == x/y).
# origin at (130, -40), 1-degree cells.
# ix: 0→[130,131), 1→[131,132), 2→[132,133), 3→[133,134), 4→[134,135)
# iy: 0→[-40,-39), 1→[-39,-38), 2→[-38,-37), 3→[-37,-36), 4→[-36,-35)
TEST_GRID = Grid(dimensions=(5, 5), origin_xy=(130.0, -40.0), cell_size=(1.0, 1.0))


def test_emissions_placed_in_lower_left_cell():
    # lon=130.5, lat=-39.5 → ix=0, iy=0
    result = gridded_livestock_emissions(
        lon=np.array([130.5]),
        lat=np.array([-39.5]),
        emissions=np.array([1.0]),
        domain_grid=TEST_GRID,
    )

    assert result[0, 0] == 1.0
    assert result.sum() == 1.0


def test_emissions_placed_in_interior_cell():
    # lon=132.5, lat=-37.5 → ix=2, iy=2
    result = gridded_livestock_emissions(
        lon=np.array([132.5]),
        lat=np.array([-37.5]),
        emissions=np.array([1.0]),
        domain_grid=TEST_GRID,
    )

    assert result[2, 2] == 1.0
    assert result.sum() == 1.0


def test_emissions_placed_in_upper_right_cell():
    # lon=134.5, lat=-35.5 → ix=4, iy=4
    result = gridded_livestock_emissions(
        lon=np.array([134.5]),
        lat=np.array([-35.5]),
        emissions=np.array([1.0]),
        domain_grid=TEST_GRID,
    )

    assert result[4, 4] == 1.0
    assert result.sum() == 1.0


def test_result_matches_grid_shape():
    result = gridded_livestock_emissions(
        lon=np.array([130.5]),
        lat=np.array([-39.5]),
        emissions=np.array([1.0]),
        domain_grid=TEST_GRID,
    )

    assert result.shape == TEST_GRID.shape


def test_zero_emissions_produce_no_emissions():
    result = gridded_livestock_emissions(
        lon=np.array([130.5]),
        lat=np.array([-39.5]),
        emissions=np.array([0.0]),
        domain_grid=TEST_GRID,
    )

    assert result.sum() == 0.0


def test_point_outside_domain_excluded():
    # lon=125.0 is west of the grid (origin_x=130), should be discarded
    result = gridded_livestock_emissions(
        lon=np.array([125.0, 130.5]),
        lat=np.array([-39.5, -39.5]),
        emissions=np.array([100.0, 1.0]),
        domain_grid=TEST_GRID,
    )

    assert result[0, 0] == 1.0
    assert result.sum() == 1.0


def test_two_points_in_same_cell_are_aggregated():
    # lon=132.2 and lon=132.7, lat=-36.8 and lat=-36.3 both → ix=2, iy=3
    result = gridded_livestock_emissions(
        lon=np.array([132.2, 132.7]),
        lat=np.array([-36.8, -36.3]),
        emissions=np.array([10.0, 5.0]),
        domain_grid=TEST_GRID,
    )

    assert result[3, 2] == 15.0
    assert result.sum() == 15.0


def test_points_in_different_cells_are_kept_separate():
    # lon=130.5, lat=-39.5 → ix=0, iy=0; lon=134.5, lat=-35.5 → ix=4, iy=4
    result = gridded_livestock_emissions(
        lon=np.array([130.5, 134.5]),
        lat=np.array([-39.5, -35.5]),
        emissions=np.array([3.0, 7.0]),
        domain_grid=TEST_GRID,
    )

    assert result[0, 0] == 3.0
    assert result[4, 4] == 7.0
    assert result.sum() == 10.0
