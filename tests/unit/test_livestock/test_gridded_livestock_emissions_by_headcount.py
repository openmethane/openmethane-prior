import pandas as pd
import pytest

from openmethane_prior.lib.grid.grid import Grid
from openmethane_prior.sectors.livestock.sector import (
    ENTERIC_ANNUAL_KG_CH4,
    gridded_livestock_emissions_by_headcount,
)

# Simple 5x5 degree grid using default EPSG:4326 projection (lon/lat == x/y).
# origin at (130, -40), 1-degree cells.
# ix: 0→[130,131), 1→[131,132), 2→[132,133), 3→[133,134), 4→[134,135)
# iy: 0→[-40,-39), 1→[-39,-38), 2→[-38,-37), 3→[-37,-36), 4→[-36,-35)
TEST_GRID = Grid(dimensions=(5, 5), origin_xy=(130.0, -40.0), cell_size=(1.0, 1.0))


def make_df(rows: list) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        columns=["lon", "lat", "heads_mapped_mix_beef", "heads_mapped_mix_sheep", "heads_mapped_dairy"],
    )


def make_row(values) -> list:
    return [values["lon"], values["lat"], values["beef"], values["sheep"], values["dairy"]]


# --- headcount scaling ---

def test_headcount_scales_emissions():
    df = make_df([
        make_row({"lon": 130.5, "lat": -39.5, "beef": 1, "sheep": 0, "dairy": 0}),
    ])

    result = gridded_livestock_emissions_by_headcount(df, TEST_GRID)

    assert result[0, 0] == pytest.approx(ENTERIC_ANNUAL_KG_CH4["beef_cattle"])


def test_sheep_headcount_scales_emissions():
    df = make_df([
        make_row({"lon": 130.5, "lat": -39.5, "beef": 0, "sheep": 1, "dairy": 0}),
    ])

    result = gridded_livestock_emissions_by_headcount(df, TEST_GRID)

    assert result[0, 0] == pytest.approx(ENTERIC_ANNUAL_KG_CH4["sheep"])


def test_dairy_headcount_scales_emissions():
    df = make_df([
        make_row({"lon": 130.5, "lat": -39.5, "beef": 0, "sheep": 0, "dairy": 1}),
    ])

    result = gridded_livestock_emissions_by_headcount(df, TEST_GRID)

    assert result[0, 0] == pytest.approx(ENTERIC_ANNUAL_KG_CH4["dairy_cattle"])


def test_mixed_headcounts_sum_correctly():
    beef, sheep, dairy = 3, 5, 7
    df = make_df([
        make_row({"lon": 130.5, "lat": -39.5, "beef": beef, "sheep": sheep, "dairy": dairy}),
    ])
    result = gridded_livestock_emissions_by_headcount(df, TEST_GRID)

    expected = (
        beef * ENTERIC_ANNUAL_KG_CH4["beef_cattle"]
        + sheep * ENTERIC_ANNUAL_KG_CH4["sheep"]
        + dairy * ENTERIC_ANNUAL_KG_CH4["dairy_cattle"]
    )
    assert result[0, 0] == pytest.approx(expected)


def test_zero_headcounts_produce_no_emissions():
    df = make_df([
        make_row({"lon": 130.5, "lat": -39.5, "beef": 0, "sheep": 0, "dairy": 0}),
    ])
    result = gridded_livestock_emissions_by_headcount(df, TEST_GRID)

    assert result.sum() == 0.0


# --- grid cell placement ---

def test_emissions_placed_in_lower_left_cell():
    # lon=130.5, lat=-39.5 → ix=0, iy=0
    df = make_df([
        make_row({"lon": 130.5, "lat": -39.5, "beef": 1, "sheep": 0, "dairy": 0}),
    ])

    result = gridded_livestock_emissions_by_headcount(df, TEST_GRID)

    assert result[0, 0] == pytest.approx(ENTERIC_ANNUAL_KG_CH4["beef_cattle"])
    assert result.sum() == pytest.approx(ENTERIC_ANNUAL_KG_CH4["beef_cattle"])


def test_emissions_placed_in_interior_cell():
    # lon=132.5, lat=-37.5 → ix=2, iy=2
    df = make_df([
        make_row({"lon": 132.5, "lat": -37.5, "beef": 0, "sheep": 0, "dairy": 1}),
    ])

    result = gridded_livestock_emissions_by_headcount(df, TEST_GRID)

    assert result[2, 2] == pytest.approx(ENTERIC_ANNUAL_KG_CH4["dairy_cattle"])
    assert result.sum() == pytest.approx(ENTERIC_ANNUAL_KG_CH4["dairy_cattle"])


def test_emissions_placed_in_upper_right_cell():
    # lon=134.5, lat=-35.5 → ix=4, iy=4
    df = make_df([
        make_row({"lon": 134.5, "lat": -35.5, "beef": 0, "sheep": 1, "dairy": 0}),
    ])

    result = gridded_livestock_emissions_by_headcount(df, TEST_GRID)

    assert result[4, 4] == pytest.approx(ENTERIC_ANNUAL_KG_CH4["sheep"])
    assert result.sum() == pytest.approx(ENTERIC_ANNUAL_KG_CH4["sheep"])


def test_point_outside_domain_excluded():
    # lon=125.0 is west of the grid (origin_x=130), should be discarded
    df = make_df([
        # outside TEST_GRID, should not be counted
        make_row({"lon": 125.0, "lat": -39.5, "beef": 100, "sheep": 100, "dairy": 100}),
        # inside TEST_GRID
        make_row({"lon": 130.5, "lat": -39.5, "beef": 1, "sheep": 0, "dairy": 0}),
    ])

    result = gridded_livestock_emissions_by_headcount(df, TEST_GRID)

    assert result.sum() == pytest.approx(ENTERIC_ANNUAL_KG_CH4["beef_cattle"])


# --- aggregation within a grid cell ---

def test_two_rows_in_same_cell_are_aggregated():
    # lon=132.2 and lon=132.7, lat=-36.8 and lat=-36.3 both → ix=2, iy=3
    beef_1, sheep_1, dairy_1 = 10, 0, 0
    beef_2, sheep_2, dairy_2 = 0, 20, 5
    df = make_df([
        make_row({"lon": 132.2, "lat": -36.8, "beef": beef_1, "sheep": sheep_1, "dairy": dairy_1}),
        make_row({"lon": 132.7, "lat": -36.3, "beef": beef_2, "sheep": sheep_2, "dairy": dairy_2}),
    ])

    result = gridded_livestock_emissions_by_headcount(df, TEST_GRID)

    expected = (
        beef_1 * ENTERIC_ANNUAL_KG_CH4["beef_cattle"]
        + sheep_1 * ENTERIC_ANNUAL_KG_CH4["sheep"]
        + dairy_1 * ENTERIC_ANNUAL_KG_CH4["dairy_cattle"]
        + beef_2 * ENTERIC_ANNUAL_KG_CH4["beef_cattle"]
        + sheep_2 * ENTERIC_ANNUAL_KG_CH4["sheep"]
        + dairy_2 * ENTERIC_ANNUAL_KG_CH4["dairy_cattle"]
    )
    assert result[3, 2] == pytest.approx(expected)
    assert result.sum() == pytest.approx(expected)


def test_three_rows_in_same_cell_are_aggregated():
    # all three → ix=1, iy=1
    df = make_df([
        make_row({"lon": 131.1, "lat": -38.9, "beef": 5, "sheep": 0, "dairy": 0}),
        make_row({"lon": 131.5, "lat": -38.5, "beef": 0, "sheep": 10, "dairy": 0}),
        make_row({"lon": 131.9, "lat": -38.1, "beef": 0, "sheep": 0, "dairy": 3}),
    ])

    result = gridded_livestock_emissions_by_headcount(df, TEST_GRID)

    expected = (
        5 * ENTERIC_ANNUAL_KG_CH4["beef_cattle"]
        + 10 * ENTERIC_ANNUAL_KG_CH4["sheep"]
        + 3 * ENTERIC_ANNUAL_KG_CH4["dairy_cattle"]
    )
    assert result[1, 1] == pytest.approx(expected)
    assert result.sum() == pytest.approx(expected)


def test_rows_in_different_cells_are_not_aggregated():
    # ix=0, iy=0 and ix=4, iy=4 are independent
    df = make_df([
        make_row({"lon": 130.5, "lat": -39.5, "beef": 10, "sheep": 0, "dairy": 0}),
        make_row({"lon": 134.5, "lat": -35.5, "beef": 0, "sheep": 0, "dairy": 7}),
    ])

    result = gridded_livestock_emissions_by_headcount(df, TEST_GRID)

    assert result[0, 0] == pytest.approx(10 * ENTERIC_ANNUAL_KG_CH4["beef_cattle"])
    assert result[4, 4] == pytest.approx(7 * ENTERIC_ANNUAL_KG_CH4["dairy_cattle"])
    assert result.sum() == pytest.approx(
        10 * ENTERIC_ANNUAL_KG_CH4["beef_cattle"] + 7 * ENTERIC_ANNUAL_KG_CH4["dairy_cattle"]
    )
