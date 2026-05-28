import datetime
import json
import numpy as np
import pandas as pd
import pytest

from openmethane_prior.data_sources.inventory import (
    inventory_data_source,
    unfccc_codes_data_source,
    get_sector_emissions_by_code,
)
from openmethane_prior.sectors import all_sectors


@pytest.fixture()
def inventory_df(input_files, data_manager):
    return data_manager.get_asset(inventory_data_source).data

@pytest.fixture()
def all_sector_meta():
    inventory_sectors = [s for s in all_sectors if s.unfccc_categories is not None]

    all_sectors_map = {}
    for sector_meta in inventory_sectors:
        all_sectors_map[sector_meta.name] = sector_meta
    return all_sectors_map


def test_inventory_get_sector_emissions_by_code(all_sector_meta, inventory_df):
    expected_annual_emissions = {
        "agriculture": 166010041.1571281,
        "coal": 901455051.0124934,
        "electricity": 11164637.314332796,
        "industrial": 2937681.1201194106,
        "livestock": 2107296329.3320558,
        "lulucf": 661762727.6374531,
        "oil_gas": 238171271.587112,
        "stationary": 73354555.56013045,
        "transport": 11702390.307919662,
        "waste": 481160233.5451011,
    }

    annual_emissions = {}
    for name in expected_annual_emissions.keys():
        annual_emissions[name] = get_sector_emissions_by_code(
            emissions_inventory=inventory_df,
            start_date=datetime.date(2022, 7, 1),
            end_date=datetime.date(2023, 6, 30),
            category_codes=all_sector_meta[name].unfccc_categories,
        )

    assert annual_emissions == pytest.approx(expected_annual_emissions)

    monthly_coal_emissions = get_sector_emissions_by_code(
        emissions_inventory=inventory_df,
        start_date=datetime.date(2023, 1, 1),
        end_date=datetime.date(2023, 1, 31),
        category_codes=all_sector_meta["coal"].unfccc_categories,
    )

    # emissions for a shorter period should be scaled from the annual emissions
    assert monthly_coal_emissions == pytest.approx(expected_annual_emissions["coal"] * (31 / 365))


def test_inventory_unfccc_codes(input_files, data_manager):
    unfccc_df = data_manager.get_asset(unfccc_codes_data_source).data
    inventory_da = data_manager.get_asset(inventory_data_source)

    # extract the raw, unmodified inventory values
    with open(inventory_da.path) as anga_file:
        inventory_json = json.load(anga_file)
        inventory_raw = pd.DataFrame.from_records(
            inventory_json["value"],
            columns=[
                "InventoryYear_ID",
                "UNFCCC_Level_1", "UNFCCC_Level_2", "UNFCCC_Level_3", "UNFCCC_Level_4",
                "Gas_Level_0",
                "Gg",
            ],
        )

    inventory_raw_ch4 = inventory_raw[inventory_raw["Gas_Level_0"] == "CH4"]
    inventory_df = inventory_da.data

    # ensure no inventory values have been "lost" during parsing or while
    # adding UNFCCC codes
    assert len(inventory_df) == len(inventory_raw_ch4)
    assert inventory_df["Gg"].sum() == inventory_raw_ch4["Gg"].sum()

    unfccc_df = unfccc_df.replace([np.nan], [None])
    _LEVEL_COLUMNS = ["UNFCCC_Level_1", "UNFCCC_Level_2", "UNFCCC_Level_3", "UNFCCC_Level_4"]
    for inx, row in inventory_df.iterrows():
        unfccc_row = unfccc_df[unfccc_df["UNFCCC_Code"] == row["UNFCCC_Code"]]

        assert len(unfccc_row) == 1, f"Too many matches for code {row['UNFCCC_Code']}"
        assert (row[_LEVEL_COLUMNS].values == unfccc_row.iloc[0][_LEVEL_COLUMNS].values).all()
