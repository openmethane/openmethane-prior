import pandas as pd
import pytest

from openmethane_prior.lib.data_manager.fetchers import (
    check_required_columns,
    google_sheet_csv_url,
)


def test_google_sheet_csv_url_from_url():
    result = google_sheet_csv_url(
        "https://docs.google.com/spreadsheets/d/EXAMPLE_SHEET_ID",
        "External facility locations",
    )

    assert result == (
        "https://docs.google.com/spreadsheets/d/EXAMPLE_SHEET_ID/gviz/tq"
        "?tqx=out:csv&headers=1&sheet=External%20facility%20locations"
    )


def test_google_sheet_csv_url_from_id():
    result = google_sheet_csv_url("EXAMPLE_SHEET_ID", "Oil and gas sites")

    assert result == (
        "https://docs.google.com/spreadsheets/d/EXAMPLE_SHEET_ID/gviz/tq"
        "?tqx=out:csv&headers=1&sheet=Oil%20and%20gas%20sites"
    )


def test_check_required_columns():
    df = pd.DataFrame(columns=["Facility name", "Notes", "Site"])

    # no exception: extra columns and order don't matter
    check_required_columns(df, ["Site", "Facility name"], "Test sheet")
    check_required_columns(df, [], "Test sheet")


def test_check_required_columns_missing():
    # a header row joined with the rows below it, as Google produces when it
    # guesses the header spans more than one row
    df = pd.DataFrame(columns=["Facility name Mine A Mine B", "Notes"])

    with pytest.raises(ValueError, match=r"'Test sheet' is missing columns \['Facility name'\]"):
        check_required_columns(df, ["Facility name"], "Test sheet")
