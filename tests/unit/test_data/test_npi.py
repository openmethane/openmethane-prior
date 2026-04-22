import datetime
import geopandas as gpd
import pandas as pd
import pytest

from openmethane_prior.data_sources.npi import filter_npi_facilities
from openmethane_prior.data_sources.npi.data import financial_year_end, financial_year_start


@pytest.fixture()
def facilities_df():
    """GeoDataFrame matching the structure returned by parse_npi_facilities_csv.

    Columns are those from the NPI facilities CSV, minus latitude/longitude
    (which are consumed to create the geometry column), plus reporting_start_date
    and reporting_end_date as computed by parse_npi_facilities_csv, after
    conversion to a projected CRS (EPSG:3577, Australian Albers).

    Facilities:
      - Alpha Gas:   oil & gas (0700), active 2020/2021–2024/2025 (max → still active)
      - Beta Gas:    oil & gas (0700), active 2018/2019–2022/2023
      - Coal Mine:   coal     (0600), active 2015/2016–2022/2023
      - Steel Works: ferrous  (2110), active 2019/2020–2021/2022
    """
    test_data = [
        # facility_id, facility_name, abn,           state, first_report_year, latest_report_year, primary_anzsic_class_code, lon,     lat
        (1001, "Alpha Gas",   "11111111111", "QLD", "2020/2021", "2024/2025", "0700", 149.0, -24.0),
        (1002, "Beta Gas",    "22222222222", "WA",  "2018/2019", "2022/2023", "0700", 117.0, -30.0),
        (1003, "Coal Mine",   "33333333333", "QLD", "2015/2016", "2022/2023", "060", 148.0, -22.0),
        (1004, "Steel Works", "44444444444", "NSW", "2019/2020", "2021/2022", "2110", 151.0, -33.0),
    ]

    df = pd.DataFrame(
        data=test_data,
        columns=[
            "facility_id", "facility_name", "abn", "state",
            "first_report_year", "latest_report_year",
            "primary_anzsic_class_code", "longitude", "latitude",
        ],
    )

    # mimic parse_npi_facilities_csv
    df["reporting_start_date"] = df["first_report_year"].map(financial_year_start)
    last_report_period = df["latest_report_year"].max()
    latest_report_year = df["latest_report_year"].replace(last_report_period, None)
    df["reporting_end_date"] = latest_report_year.map(financial_year_end)
    gdf = gpd.GeoDataFrame(
        data=df.drop(columns=["longitude", "latitude"]),
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="EPSG:4326",
    ).to_crs("EPSG:3577")


    return gdf


# --- period filtering ---

def test_filter_npi_all_active_period(facilities_df):
    # period where all facilities were reporting
    result = filter_npi_facilities(
        facilities_df,
        period_start=datetime.date(2021, 7, 1),
        period_end=datetime.date(2021, 7, 31),
    )
    assert len(result) == 4
    assert set(result["facility_name"]) == {"Alpha Gas", "Beta Gas", "Coal Mine", "Steel Works"}


def test_filter_npi_before_any_start(facilities_df):
    # period before the earliest first_report_year (2015/2016 → 2015-07-01)
    result = filter_npi_facilities(
        facilities_df,
        period_start=datetime.date(2010, 1, 1),
        period_end=datetime.date(2010, 12, 31),
    )
    assert len(result) == 0


def test_filter_npi_only_still_active(facilities_df):
    # period well after all non-active facilities have closed:
    # latest_report_year max is 2024/2025 → Alpha Gas gets end_date=None (still active).
    # Beta Gas and Coal Mine both have latest 2022/2023 → end_date = 2023-07-01.
    # Steel Works has latest 2021/2022 → end_date = 2022-07-01.
    # A period starting 2023-07-01 excludes all except Alpha Gas.
    result = filter_npi_facilities(
        facilities_df,
        period_start=datetime.date(2023, 7, 1),
        period_end=datetime.date(2024, 6, 30),
    )

    assert len(result) == 1
    assert set(result["facility_name"]) == {"Alpha Gas"}


def test_filter_npi_boundary_latest_report_year(facilities_df):
    # end_date for "2022/2023" is 2023-06-30. A period_start of exactly 2023-07-01 still
    # includes Beta Gas and Coal Mine (>= boundary).
    result = filter_npi_facilities(
        facilities_df,
        period_start=datetime.date(2023, 7, 1),
        period_end=datetime.date(2023, 7, 1),
    )

    assert set(result["facility_name"]) == {"Alpha Gas"}

    result = filter_npi_facilities(
        facilities_df,
        period_start=datetime.date(2023, 6, 30),
        period_end=datetime.date(2023, 6, 30),
    )

    assert set(result["facility_name"]) == {'Alpha Gas', 'Beta Gas', 'Coal Mine'}


def test_filter_npi_excludes_facility_before_start(facilities_df):
    # Alpha Gas first_report_year is 2020/2021 → start_date = 2020-07-01.
    # A period ending before that date should not include Alpha Gas.
    result = filter_npi_facilities(
        facilities_df,
        period_start=datetime.date(2019, 7, 1),
        period_end=datetime.date(2019, 7, 31),
    )
    assert "Alpha Gas" not in set(result["facility_name"])
    # Beta Gas, Coal Mine active since earlier FYs; Steel Works starts 2019-07-01.
    assert "Beta Gas" in set(result["facility_name"])
    assert "Coal Mine" in set(result["facility_name"])
    assert "Steel Works" in set(result["facility_name"])


# --- ANZSIC filtering ---

def test_filter_npi_anzsic_oil_gas(facilities_df):
    result = filter_npi_facilities(
        facilities_df,
        period_start=datetime.date(2021, 7, 1),
        period_end=datetime.date(2021, 7, 31),
        anzsic_codes=["070"],
    )

    assert len(result) == 2
    assert set(result["facility_name"]) == {"Alpha Gas", "Beta Gas"}


def test_filter_npi_anzsic_coal(facilities_df):
    result = filter_npi_facilities(
        facilities_df,
        period_start=datetime.date(2021, 7, 1),
        period_end=datetime.date(2021, 7, 31),
        anzsic_codes=["06"],
    )

    assert len(result) == 1
    assert set(result["facility_name"]) == {"Coal Mine"}


def test_filter_npi_anzsic_four_digit_code(facilities_df):
    # 4-digit code "2110" simplifies to "211"; "2110".startswith("211") is True
    result = filter_npi_facilities(
        facilities_df,
        period_start=datetime.date(2021, 7, 1),
        period_end=datetime.date(2021, 7, 31),
        anzsic_codes=["2110"],
    )

    assert len(result) == 1
    assert set(result["facility_name"]) == {"Steel Works"}



def test_filter_npi_anzsic_multiple_codes(facilities_df):
    result = filter_npi_facilities(
        facilities_df,
        period_start=datetime.date(2021, 7, 1),
        period_end=datetime.date(2021, 7, 31),
        anzsic_codes=["070", "06"],
    )

    assert len(result) == 3
    assert set(result["facility_name"]) == {"Alpha Gas", "Beta Gas", "Coal Mine"}


def test_filter_npi_anzsic_no_match(facilities_df):
    result = filter_npi_facilities(
        facilities_df,
        period_start=datetime.date(2021, 7, 1),
        period_end=datetime.date(2021, 7, 31),
        anzsic_codes=["9999"],
    )

    assert len(result) == 0


def test_filter_npi_anzsic_none_returns_all_in_period(facilities_df):
    # anzsic_codes=None (the default) applies no ANZSIC filter, returning all
    # facilities active in the period
    result_no_filter = filter_npi_facilities(
        facilities_df,
        period_start=datetime.date(2021, 7, 1),
        period_end=datetime.date(2021, 7, 31),
    )
    result_with_none = filter_npi_facilities(
        facilities_df,
        period_start=datetime.date(2021, 7, 1),
        period_end=datetime.date(2021, 7, 31),
        anzsic_codes=None,
    )
    pd.testing.assert_frame_equal(result_no_filter, result_with_none)


# --- combined period + ANZSIC ---

def test_filter_npi_combined(facilities_df):
    # period after Steel Works closed (2023-07-02+) and only oil/gas ANZSIC
    result = filter_npi_facilities(
        facilities_df,
        period_start=datetime.date(2023, 7, 2),
        period_end=datetime.date(2024, 6, 30),
        anzsic_codes=["070"],
    )

    assert len(result) == 1
    assert set(result["facility_name"]) == {"Alpha Gas"}


def test_filter_npi_combined_no_results(facilities_df):
    # period before Alpha Gas started, filtered to oil/gas only → no results
    result = filter_npi_facilities(
        facilities_df,
        period_start=datetime.date(2019, 7, 1),
        period_end=datetime.date(2019, 7, 31),
        anzsic_codes=["070"],
    )

    assert "Alpha Gas" not in set(result["facility_name"])
    assert "Beta Gas" in set(result["facility_name"])

# --- still-active facility (max latest_report_year) ---

def test_filter_npi_max_latest_report_year_treated_as_active(facilities_df):
    # The facility with the maximum latest_report_year ("2024/2025") should
    # have its end_date set to None, making it active indefinitely.
    # Request a period far in the future — only Alpha Gas should appear.
    result = filter_npi_facilities(
        facilities_df,
        period_start=datetime.date(2030, 1, 1),
        period_end=datetime.date(2030, 12, 31),
    )

    assert "Alpha Gas" in set(result["facility_name"])
