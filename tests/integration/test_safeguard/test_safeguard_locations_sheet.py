from openmethane_prior.data_sources.safeguard.data import (
    safeguard_locations_columns,
    safeguard_locations_data_source,
)
from openmethane_prior.lib.data_manager.fetchers import fetch_google_sheet_by_name_csv


def test_fetch_external_facility_locations_sheet():
    result = fetch_google_sheet_by_name_csv(
        safeguard_locations_data_source.url,
        "External facility locations",
        list(safeguard_locations_columns),
    )

    # every row of the sheet is data, rather than being joined into the
    # header as happens when Google guesses the header spans many rows
    assert len(result) > 100
    assert all(len(column) < 50 for column in result.columns)
