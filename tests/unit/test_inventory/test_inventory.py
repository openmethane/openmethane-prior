import datetime
import pytest
import pandas as pd

from openmethane_prior.data_sources.inventory.data import _find_unfccc_code
from openmethane_prior.data_sources.inventory.inventory import get_sector_emissions_by_code


@pytest.fixture()
def unfccc_df():
    return pd.DataFrame(
        [
            ("1",       "Energy",                          None,                            None,    None),
            ("1.A",     "Energy",                          "Fuel Combustion",               None,    None),
            ("1.A.1",   "Energy",                          "Fuel Combustion",               "Other", None),
            ("1.A.1.a", "Energy",                          "Fuel Combustion",               "Other", "Mobile"),
            ("1.B",     "Energy",                          "Fugitive Emissions From Fuels", None,    None),
            ("2",       "Industrial Processes",            None,                            None,    None),
        ],
        columns=["UNFCCC_Code", "UNFCCC_Level_1", "UNFCCC_Level_2", "UNFCCC_Level_3", "UNFCCC_Level_4"],
    )


def make_row(level_1, level_2, level_3, level_4):
    return pd.Series({
        "UNFCCC_Level_1": level_1,
        "UNFCCC_Level_2": level_2,
        "UNFCCC_Level_3": level_3,
        "UNFCCC_Level_4": level_4,
    })


def test_find_unfccc_code_exact(unfccc_df):
    row = make_row("Energy", "Fuel Combustion", "Other", "Mobile")
    assert _find_unfccc_code(row, unfccc_df) == "1.A.1.a"


def test_find_unfccc_code_fallback_drops_level4(unfccc_df):
    # "Smoke from AI fires" has no exact Level_4 match; should fall back to "1.B"
    row = make_row("Energy", "Fugitive Emissions From Fuels", "Smoke", "Smoke from AI fires")
    assert _find_unfccc_code(row, unfccc_df) == "1.B"


def test_find_unfccc_code_fallback_drops_level3_and_4(unfccc_df):
    # No match on Level_3 or Level_4; should fall back to "1.B" via Level_1 + Level_2
    row = make_row("Energy", "Fugitive Emissions From Fuels", "Unknown L3", "Unknown L4")
    assert _find_unfccc_code(row, unfccc_df) == "1.B"


def test_find_unfccc_code_no_match(unfccc_df):
    row = make_row("Unknown sector", "Unknown L2", "Unknown L3", "Unknown L4")
    assert _find_unfccc_code(row, unfccc_df) is None


def make_inventory_df(entries):
    """Build a test emissions inventory DataFrame.

    Each entry: (year, unfccc_code, ch4_kg).
    """
    return pd.DataFrame(entries, columns=["InventoryYear_ID", "UNFCCC_Code", "ch4_kg"])


def test_inventory_get_sector_emissions_by_code():
    inventory = make_inventory_df([
        (1993, "1.A.1.a", 1.1 * 1e6),
        (1994, "1.A.1.a", 2.2 * 1e6),
        (1995, "1.A.1.a", 3.3 * 1e6),
        (1993, "1.B",     0.2 * 1e6),
        (1994, "1.B",     0.5 * 1e6),
        (1995, "1.B",     0.8 * 1e6),
        (1993, "2",       0.7 * 1e6),
        (1994, "2",       0.11 * 1e6),
        (1995, "2",       0.13 * 1e6),
    ])

    energy_emissions = get_sector_emissions_by_code(
        emissions_inventory=inventory,
        category_codes=["1"],
        start_date=datetime.date(1993, 1, 1),
        end_date=datetime.date(1993, 1, 31),
    )
    assert energy_emissions == pytest.approx((1.1 + 0.2) * (31 / 365) * 1e6)

    multi_emissions = get_sector_emissions_by_code(
        emissions_inventory=inventory,
        category_codes=["1.A", "2"], # multiple codes
        start_date=datetime.date(1993, 1, 1),
        end_date=datetime.date(1993, 1, 31),
    )
    assert multi_emissions == pytest.approx((1.1 + 0.7) * (31 / 365) * 1e6)

    future_emissions = get_sector_emissions_by_code(
        emissions_inventory=inventory,
        category_codes=["1.A", "2"], # multiple codes
        start_date=datetime.date(1997, 1, 1),
        end_date=datetime.date(1997, 1, 31),
    )
    # No 1997 data — uses last available year (1995)
    assert future_emissions == pytest.approx((3.3 + 0.13) * (31 / 365) * 1e6)

    past_emissions = get_sector_emissions_by_code(
        emissions_inventory=inventory,
        category_codes=["1.A", "2"], # multiple codes
        start_date=datetime.date(1990, 1, 1),
        end_date=datetime.date(1990, 1, 31),
    )
    # No 1990 data — uses first available year (1993)
    assert past_emissions == pytest.approx((1.1 + 0.7) * (31 / 365) * 1e6)
