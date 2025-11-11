import pandas as pd
import pytest

from openmethane_prior.data_sources.safeguard.data import safeguard_locations_csv_columns
from openmethane_prior.data_sources.safeguard.location import (
    filter_locations,
    get_safeguard_facility_locations,
)
from openmethane_prior.data_sources.safeguard.facility import create_facilities_from_safeguard_rows


@pytest.fixture()
def location_rows_df():
    return pd.DataFrame(
        data=[
            ("Facility Name A", "test-ds", "id-001a"),
            ("Facility Name A", "test-ds", "id-001b"),
            ("Facility Name A", "test-ds", "id-001c"),
            ("Facility Name B", "test-ds", "id-002"),
            ("Facility Name C", "alternate-ds", "id-003"),
            ("Facility Name D", "alternate-ds", "id-004"),
        ],
        columns=safeguard_locations_csv_columns,
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

    assert len(test_locations_c) == 4
    assert set(test_locations_c.data_source_id) == {"id-001a", "id-001b", "id-001c", "id-002"}

    test_locations_c_with_id = filter_locations(
        location_rows_df,
        data_source_name="test-ds",
        data_source_id="id-001a",
    )

    assert len(test_locations_c_with_id) == 1
    assert set(test_locations_c_with_id.data_source_id) == {"id-001a"}

    test_locations_d = filter_locations(location_rows_df, data_source_name="alternate-ds")

    assert len(test_locations_d) == 2
    assert set(test_locations_d.data_source_id) == {"id-003", "id-004"}

    test_locations_ds_not_found = filter_locations(location_rows_df, data_source_name="unknown-ds")

    assert len(test_locations_ds_not_found) == 0


def test_locations_get_safeguard_facility_locations(location_rows_df):
    safeguard_facilities_df = create_facilities_from_safeguard_rows(pd.DataFrame(
        data=[
            ("Facility Name A", "NSW", "Basic ferrous metal manufacturing (211)", 123.0),
            ("Facility Name C", "NSW", "Basic ferrous product manufacturing (212)", 456.0),
        ],
        columns=["facility_name", "state", "anzsic", "co2e_ch4"],
    ), (2023, 2024), 28)

    test_facilities, test_locations = get_safeguard_facility_locations(
        safeguard_facilities_df=safeguard_facilities_df,
        locations_df=location_rows_df,
        data_source_name="test-ds",
    )

    assert len(test_facilities) == 1
    assert set(test_facilities.facility_name) == {"Facility Name A"}

    assert len(test_locations) == 4
    assert set(test_locations.safeguard_facility_name) == {"Facility Name A", "Facility Name B"}
    assert set(test_locations.data_source_id) == {"id-001a", "id-001b", "id-001c", "id-002"}
