import datetime

import pandas as pd
import pytest

from openmethane_prior.data_sources.safeguard.facility import (
    create_facilities_from_safeguard_rows,
    filter_facilities,
    parse_anzsic_code,
)

@pytest.fixture()
def facility_rows_df():
    test_data = [
        ("Ironic",      "NSW", "Basic ferrous metal manufacturing (211)", 123.0),
        ("Iron Giant",  "NSW", "Basic ferrous product manufacturing (212)", 456.0),
        ("Al to Zn",    "NSW", "Basic non-ferrous metal manufacturing (213)", 789.0),
        ("Days of Ore", "NSW", "Metal ore mining (080)", 1111.0),
    ]
    return pd.DataFrame(
        data=test_data,
        columns=["facility_name", "state", "anzsic", "co2e_ch4"],
    )


def test_parse_anzsic_code():
    assert parse_anzsic_code("Coal mining (060)") == "060"
    assert parse_anzsic_code("Oil and gas extraction (070)") == "070"
    assert parse_anzsic_code("Cement, lime, plaster and concrete product manufacturing (203)") == "203"
    assert parse_anzsic_code("Waste treatment, disposal and remediation services (292)") == "292"


def test_safeguard_create_facilities_from_safeguard_rows():
    facility_rows_df = pd.DataFrame(
        data=[
            ("Ironic",      "NSW", "Basic ferrous metal manufacturing (211)", 123.0),
            ("Iron Giant",  "NSW", "Basic ferrous product manufacturing (212)", 456.0),
            ("Al to Zn",    "NSW", "Basic non-ferrous metal manufacturing (213)", 789.0),
            ("Days of Ore", "NSW", "Metal ore mining (080)", 1111.0),
            ("Days of Ore", "NSW", "Metal ore mining (080)", 2000.0), # change of ownership
        ],
        columns=["facility_name", "state", "anzsic", "co2e_ch4"],
    )

    facilities_df = create_facilities_from_safeguard_rows(facility_rows_df, (2024, 2025), 28)

    assert len(facilities_df) == 4 # 5 rows, 2 duplicates

    facility_combined = facilities_df[facilities_df["facility_name"] == "Days of Ore"].loc[1]

    assert facility_combined.facility_name == "Days of Ore"
    assert facility_combined.state == "NSW"
    assert facility_combined.anzsic == "Metal ore mining (080)"
    assert facility_combined.anzsic_code == "080"
    assert facility_combined.co2e_ch4 == 1111.0 + 2000.0
    assert facility_combined.ch4_kg == (1111.0 + 2000.0) * 1000 * (1 / 28)
    assert facility_combined.reporting_start == datetime.date(2024, 7, 1)
    assert facility_combined.reporting_end == datetime.date(2025, 6, 30)


def test_safeguard_filter_facilities(facility_rows_df):
    facilities_df = create_facilities_from_safeguard_rows(
        safeguard_rows_df=facility_rows_df,
        reporting_period=(2023, 2024), # 2023-07-01 to 2024-06-30
        ch4_gwp=28,
    )

    # filter by anzsic
    test_metal_manufacturers = filter_facilities(facilities_df, anzsic_codes=["21"])

    assert len(test_metal_manufacturers) == 3
    assert set(test_metal_manufacturers.facility_name) == {"Ironic", "Iron Giant", "Al to Zn"}
    pd.testing.assert_frame_equal(filter_facilities(facilities_df, anzsic_codes=["210"]), test_metal_manufacturers)
    pd.testing.assert_frame_equal(filter_facilities(facilities_df, anzsic_codes=["2100"]), test_metal_manufacturers)

    test_iron_manufacturers = filter_facilities(facilities_df, anzsic_codes=["211", "212"])

    assert len(test_iron_manufacturers) == 2
    assert set(test_iron_manufacturers.facility_name) == {"Ironic", "Iron Giant"}
    pd.testing.assert_frame_equal(filter_facilities(facilities_df, anzsic_codes=["2110", "2120"]), test_iron_manufacturers)

    test_iron_mines = filter_facilities(facilities_df, anzsic_codes=["08"])

    assert len(test_iron_mines) == 1
    assert set(test_iron_mines.facility_name) == {"Days of Ore"}
    pd.testing.assert_frame_equal(filter_facilities(facilities_df, anzsic_codes=["0800"]), test_iron_mines)

    # filter by period
    outside_reporting_dates = [
        (datetime.date(2023, 1, 1), datetime.date(2023, 1, 31)),
        (datetime.date(2023, 6, 30), datetime.date(2023, 6, 30)),
        (datetime.date(2023, 1, 1), datetime.date(2023, 12, 12)),
        (datetime.date(2024, 7, 1), datetime.date(2024, 7, 1)),
        (datetime.date(2024, 1, 1), datetime.date(2024, 7, 1)),
    ]
    for period in outside_reporting_dates:
        # these periods have a date which falls outside the reporting period,
        # so no results are returned
        assert len(filter_facilities(facilities_df, period=period)) == 0

    within_reporting_dates = [
        (datetime.date(2023, 7, 1), datetime.date(2023, 7, 1)),
        (datetime.date(2024, 6, 30), datetime.date(2024, 6, 30)),
        (datetime.date(2023, 7, 1), datetime.date(2024, 6, 30)),
        (datetime.date(2024, 1, 1), datetime.date(2024, 1, 31)),
    ]
    for period in within_reporting_dates:
        # these periods fall completely within the reporting period, so the
        # full results are returned
        pd.testing.assert_frame_equal(filter_facilities(facilities_df, period=period), facilities_df)

    # multiple filters
    test_multiple_filters_in_period = filter_facilities(
        facilities_df,
        anzsic_codes=["21"],
        period=(datetime.date(2023, 7, 1), datetime.date(2023, 7, 1)),
    )
    pd.testing.assert_frame_equal(test_multiple_filters_in_period, test_metal_manufacturers)

    test_multiple_filters_outside_period = filter_facilities(
        facilities_df,
        anzsic_codes=["21"],
        period=(datetime.date(2023, 1, 1), datetime.date(2023, 1, 31)),
    )
    assert len(test_multiple_filters_outside_period) == 0
