import io

import pandas as pd
import pytest

from openmethane_prior.data_sources.financial_year import FinancialYear
from openmethane_prior.data_sources.safeguard.data import (
    check_location_year_columns,
    read_location_csv,
)
from openmethane_prior.data_sources.safeguard.location import (
    filter_locations,
    filter_locations_for_financial_year,
    get_safeguard_facility_locations,
)
from openmethane_prior.data_sources.safeguard.facility import create_facilities_from_safeguard_rows


@pytest.fixture()
def safeguard_facilities_df():
    return create_facilities_from_safeguard_rows(pd.DataFrame(
        data=[
            ("Facility Name A", "NSW", "Basic ferrous metal manufacturing (211)", 123.0),
            ("Facility Name B", "NSW", "Basic ferrous metal manufacturing (211)", 111.0),
            ("Facility Name B", "NSW", "Basic ferrous metal manufacturing (211)", 222.0),
            ("Facility Name C", "NSW", "Basic ferrous metal manufacturing (211)", 400.0),
            ("Facility Name C", "NSW", "Basic ferrous metal manufacturing (211)", 500.0),
            ("Facility Name D", "NSW", "Basic ferrous metal manufacturing (211)", 600.0),
            ("Facility Name E", "NSW", "Basic ferrous metal manufacturing (211)", 700.0),
            ("Facility Name F", "NSW", "Basic ferrous product manufacturing (212)", 456.0),
        ],
        columns=["facility_name", "state", "anzsic", "co2e_ch4"],
    ), FinancialYear(2023), 28)

@pytest.fixture()
def location_rows_df():
    return pd.DataFrame(
        data=[
            ("Facility Name A", "test-ds", "id-001a"),
            ("Facility Name A", "test-ds", "id-001b"),
            ("Facility Name A", "test-ds", "id-001c"),
            ("Facility Name B", "test-ds", "id-002"),
            ("Facility Name C", "test-ds", "id-003"),
            ("Facility Name E", "alternate-ds", "id-005"),
        ],
        columns=["safeguard_facility_name", "data_source_name", "data_source_id"],
    )

def test_locations_filter_locations(location_rows_df):
    # by facility id
    test_locations_a = filter_locations(location_rows_df, "Facility Name A")

    assert len(test_locations_a) == 3
    assert set(test_locations_a.data_source_id) == {"id-001a", "id-001b", "id-001c"}

    test_locations_b = filter_locations(location_rows_df, "Facility Name B")

    assert len(test_locations_b) == 1
    assert set(test_locations_b.data_source_id) == {"id-002"}

    test_locations_not_found = filter_locations(location_rows_df, "Facility Name 404")

    assert len(test_locations_not_found) == 0

    # by data source
    test_locations_c = filter_locations(location_rows_df, data_source_name="test-ds")

    assert len(test_locations_c) == 5
    assert set(test_locations_c.data_source_id) == {"id-001a", "id-001b", "id-001c", "id-002", "id-003"}

    test_locations_c_with_id = filter_locations(
        location_rows_df,
        data_source_name="test-ds",
        data_source_id="id-001a",
    )

    assert len(test_locations_c_with_id) == 1
    assert set(test_locations_c_with_id.data_source_id) == {"id-001a"}

    test_locations_d = filter_locations(location_rows_df, data_source_name="alternate-ds")

    assert len(test_locations_d) == 1
    assert set(test_locations_d.data_source_id) == {"id-005"}

    test_locations_ds_not_found = filter_locations(location_rows_df, data_source_name="unknown-ds")

    assert len(test_locations_ds_not_found) == 0


def test_locations_get_safeguard_facility_locations(safeguard_facilities_df, location_rows_df):
    test_facilities, test_locations = get_safeguard_facility_locations(
        safeguard_facilities_df=safeguard_facilities_df,
        locations_df=location_rows_df,
        data_source_name="test-ds",
    )

    # facilities not in the locations dataset have been filtered out
    assert len(test_facilities) == 3
    assert set(test_facilities.facility_name) == {"Facility Name A", "Facility Name B", "Facility Name C"}

    # locations not correlated with a facility have been filtered out
    assert len(test_locations) == 5
    assert set(test_locations.safeguard_facility_name) == {"Facility Name A", "Facility Name B", "Facility Name C"}
    assert set(test_locations.data_source_id) == {"id-001a", "id-001b", "id-001c", "id-002", "id-003"}


@pytest.fixture()
def year_limited_location_rows_df():
    # Facility B absorbed another facility's mine (id-002b) from FY 2024-25,
    # and Facility C's original site (id-003a) closed after FY 2023-24
    return pd.DataFrame(
        data=[
            ("Facility Name A", "test-ds", "id-001", None, None),
            ("Facility Name B", "test-ds", "id-002a", None, None),
            ("Facility Name B", "test-ds", "id-002b", "2024-25", None),
            ("Facility Name C", "test-ds", "id-003a", None, "2023-24"),
            ("Facility Name C", "test-ds", "id-003b", "2024-25", ""),
        ],
        columns=[
            "safeguard_facility_name", "data_source_name", "data_source_id",
            "first_financial_year", "last_financial_year",
        ],
    )


def test_filter_locations_for_financial_year_before_change(year_limited_location_rows_df):
    result = filter_locations_for_financial_year(
        year_limited_location_rows_df, FinancialYear(2023),
    )

    assert list(result["data_source_id"]) == ["id-001", "id-002a", "id-003a"]


def test_filter_locations_for_financial_year_after_change(year_limited_location_rows_df):
    result = filter_locations_for_financial_year(
        year_limited_location_rows_df, FinancialYear(2024),
    )

    assert list(result["data_source_id"]) == ["id-001", "id-002a", "id-002b", "id-003b"]


def test_filter_locations_for_financial_year_no_year_columns(location_rows_df):
    result = filter_locations_for_financial_year(location_rows_df, FinancialYear(2024))

    pd.testing.assert_frame_equal(result, location_rows_df)


def test_filter_locations_for_financial_year_invalid_label(year_limited_location_rows_df):
    year_limited_location_rows_df.loc[0, "first_financial_year"] = "2024-2025"

    with pytest.raises(ValueError, match="invalid financial year '2024-2025'"):
        filter_locations_for_financial_year(year_limited_location_rows_df, FinancialYear(2024))


def test_filter_locations_for_financial_year_reversed_range(year_limited_location_rows_df):
    year_limited_location_rows_df.loc[0, "first_financial_year"] = "2024-25"
    year_limited_location_rows_df.loc[0, "last_financial_year"] = "2023-24"

    match = r"first financial year after their last: \['Facility Name A'\]"
    with pytest.raises(ValueError, match=match):
        filter_locations_for_financial_year(year_limited_location_rows_df, FinancialYear(2024))


location_csv = (
    "Facility name,Supporting data source,Supporting data id,"
    "First financial year,Last financial year,Notes\n"
    "Facility Name A,test-ds,id-001,,,a note\n"
    "Facility Name B,test-ds,533928,2024-25,,\n"
    "Facility Name C,test-ds,,,,deliberately unlocated\n"
)


def test_read_location_csv():
    result = read_location_csv(io.StringIO(location_csv))

    expected = pd.DataFrame({
        "safeguard_facility_name": ["Facility Name A", "Facility Name B"],
        "data_source_name": ["test-ds", "test-ds"],
        "data_source_id": ["id-001", "533928"],
    })
    pd.testing.assert_frame_equal(result, expected)


def test_read_location_csv_financial_year():
    result_2023 = read_location_csv(
        io.StringIO(location_csv), financial_year=FinancialYear(2023),
    )
    result_2024 = read_location_csv(
        io.StringIO(location_csv), financial_year=FinancialYear(2024),
    )

    assert list(result_2023["data_source_id"]) == ["id-001"]
    assert list(result_2024["data_source_id"]) == ["id-001", "533928"]


def test_read_location_csv_reordered_columns():
    csv = (
        "Notes,Supporting data id,Facility name,Supporting data source\n"
        ",id-001,Facility Name A,test-ds\n"
    )

    result = read_location_csv(io.StringIO(csv))

    assert result.to_dict(orient="records") == [{
        "safeguard_facility_name": "Facility Name A",
        "data_source_name": "test-ds",
        "data_source_id": "id-001",
    }]


def test_read_location_csv_header_whitespace():
    csv = (
        "Facility name ,Supporting data source,Supporting data id, First financial year\n"
        "Facility Name A,test-ds,id-001,2024-25\n"
    )

    result = read_location_csv(io.StringIO(csv), financial_year=FinancialYear(2023))

    assert len(result) == 0


def test_read_location_csv_missing_column():
    csv = "Facility name,Supporting data source\nFacility Name A,test-ds\n"

    with pytest.raises(KeyError):
        read_location_csv(io.StringIO(csv))


def test_check_location_year_columns():
    # no exception: expected year columns, or none at all
    check_location_year_columns(["Facility name", "First financial year", "Last financial year"])
    check_location_year_columns(["Facility name", "Notes"])


@pytest.mark.parametrize("column", [
    "First Financial Year",
    "First financial years",
    "Last year",
    "First FY",
])
def test_check_location_year_columns_unexpected(column):
    with pytest.raises(ValueError, match="look like financial year columns"):
        check_location_year_columns(["Facility name", column])
