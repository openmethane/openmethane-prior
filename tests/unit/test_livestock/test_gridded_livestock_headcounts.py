import pandas as pd

from openmethane_prior.lib.grid.grid import Grid
from openmethane_prior.sectors.livestock.sector import (
    gridded_livestock_headcounts,
)

# Simple 5x5 degree grid using default EPSG:4326 projection (lon/lat == x/y).
# origin at (130, -40), 1-degree cells.
# ix: 0→[130,131), 1→[131,132), 2→[132,133), 3→[133,134), 4→[134,135)
# iy: 0→[-40,-39), 1→[-39,-38), 2→[-38,-37), 3→[-37,-36), 4→[-36,-35)
TEST_GRID = Grid(dimensions=(5, 5), origin_xy=(130.0, -40.0), cell_size=(1.0, 1.0))


def make_df(rows: list) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        columns=["lon", "lat", "heads_mapped_mix_beef", "heads_mapped_dairy", "heads_mapped_mix_sheep"],
    )


def make_row(values) -> list:
    return [values["lon"], values["lat"], values["beef"], values["dairy"], values["sheep"]]


# --- headcount placement ---

def test_headcount_placement_beef():
    df = make_df([
        make_row({"lon": 130.5, "lat": -39.5, "beef": 1, "dairy": 0, "sheep": 0}),
    ])

    result_beef, result_dairy, result_sheep = gridded_livestock_headcounts(df, TEST_GRID)

    assert result_beef[0, 0] == 1
    assert result_beef.sum() == 1
    assert result_dairy.sum() == 0
    assert result_sheep.sum() == 0


def test_headcount_placement_dairy():
    df = make_df([
        make_row({"lon": 130.5, "lat": -39.5, "beef": 0, "dairy": 1, "sheep": 0}),
    ])

    result_beef, result_dairy, result_sheep = gridded_livestock_headcounts(df, TEST_GRID)

    assert result_beef.sum() == 0
    assert result_dairy[0, 0] == 1
    assert result_dairy.sum() == 1
    assert result_sheep.sum() == 0


def test_headcount_placement_sheep():
    df = make_df([
        make_row({"lon": 130.5, "lat": -39.5, "beef": 0, "dairy": 0, "sheep": 1}),
    ])

    result_beef, result_dairy, result_sheep = gridded_livestock_headcounts(df, TEST_GRID)

    assert result_beef.sum() == 0
    assert result_dairy.sum() == 0
    assert result_sheep[0, 0] == 1
    assert result_sheep.sum() == 1


def test_headcount_placement_mixed():
    beef, sheep, dairy = 3, 5, 7
    df = make_df([
        make_row({"lon": 130.5, "lat": -39.5, "beef": beef, "dairy": dairy, "sheep": sheep}),
    ])
    result_beef, result_dairy, result_sheep = gridded_livestock_headcounts(df, TEST_GRID)

    assert result_beef[0, 0] == beef
    assert result_dairy[0, 0] == dairy
    assert result_sheep[0, 0] == sheep


def test_zero_headcounts_produce_no_emissions():
    df = make_df([
        make_row({"lon": 130.5, "lat": -39.5, "beef": 0, "dairy": 0, "sheep": 0}),
    ])
    result_beef, result_dairy, result_sheep = gridded_livestock_headcounts(df, TEST_GRID)

    assert result_beef.sum() == 0.0
    assert result_dairy.sum() == 0.0
    assert result_sheep.sum() == 0.0


# --- grid cell placement ---

def test_emissions_placed_in_lower_left_cell():
    # lon=130.5, lat=-39.5 → ix=0, iy=0
    df = make_df([
        make_row({"lon": 130.5, "lat": -39.5, "beef": 1, "dairy": 0, "sheep": 0}),
    ])

    result_beef, _, _ = gridded_livestock_headcounts(df, TEST_GRID)

    assert result_beef[0, 0] == 1
    assert result_beef.sum() == 1


def test_emissions_placed_in_interior_cell():
    # lon=132.5, lat=-37.5 → ix=2, iy=2
    df = make_df([
        make_row({"lon": 132.5, "lat": -37.5, "beef": 0, "dairy": 1, "sheep": 0}),
    ])

    _, result_dairy, _ = gridded_livestock_headcounts(df, TEST_GRID)

    assert result_dairy[2, 2] == 1
    assert result_dairy.sum() == 1


def test_emissions_placed_in_upper_right_cell():
    # lon=134.5, lat=-35.5 → ix=4, iy=4
    df = make_df([
        make_row({"lon": 134.5, "lat": -35.5, "beef": 0, "dairy": 0, "sheep": 1}),
    ])

    _, _, result_sheep = gridded_livestock_headcounts(df, TEST_GRID)

    assert result_sheep[4, 4] == 1
    assert result_sheep.sum() == 1


def test_point_outside_domain_excluded():
    # lon=125.0 is west of the grid (origin_x=130), should be discarded
    df = make_df([
        # outside TEST_GRID, should not be counted
        make_row({"lon": 125.0, "lat": -39.5, "beef": 100, "dairy": 100, "sheep": 100}),
        # inside TEST_GRID
        make_row({"lon": 130.5, "lat": -39.5, "beef": 1, "dairy": 0, "sheep": 0}),
    ])

    result_beef, result_dairy, result_sheep = gridded_livestock_headcounts(df, TEST_GRID)

    assert result_beef.sum() == 1
    assert result_dairy.sum() == 0
    assert result_sheep.sum() == 0


# --- aggregation within a grid cell ---

def test_two_rows_in_same_cell_are_aggregated():
    # lon=132.2 and lon=132.7, lat=-36.8 and lat=-36.3 both → ix=2, iy=3
    beef_1, dairy_1, sheep_1 = 10, 0, 0
    beef_2, dairy_2, sheep_2 = 0, 5, 20
    df = make_df([
        make_row({"lon": 132.2, "lat": -36.8, "beef": beef_1, "dairy": dairy_1, "sheep": sheep_1}),
        make_row({"lon": 132.7, "lat": -36.3, "beef": beef_2, "dairy": dairy_2, "sheep": sheep_2}),
    ])

    result_beef, result_dairy, result_sheep = gridded_livestock_headcounts(df, TEST_GRID)

    assert result_beef[3, 2] == beef_1 + beef_2
    assert result_dairy[3, 2] == dairy_1 + dairy_2
    assert result_sheep[3, 2] == sheep_1 + sheep_2
