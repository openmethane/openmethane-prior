import logging

import numpy as np
import pandas as pd
import pytest

from openmethane_prior.lib.grid.grid import Grid
from openmethane_prior.sectors.coal.safeguard_coal import allocate_safeguard_facility_emissions


@pytest.fixture()
def domain_grid():
    # EPSG:4326 grid, so cell (x, y) covers lon x..x+1, lat y..y+1
    return Grid(dimensions=(4, 4), origin_xy=(0, 0), cell_size=(1, 1))


@pytest.fixture()
def coal_facilities_df():
    # mines have one row per emissions period, with repeated coordinates
    return pd.DataFrame(
        data=[
            ("Mine A", 0.5, 0.5),
            ("Mine A", 0.5, 0.5),
            ("Mine B", 2.5, 1.5),
            ("Mine C", 3.5, 3.5),
            ("Mine Outside", 10.5, 10.5),
        ],
        columns=["source_name", "lon", "lat"],
    )


def facility_locations(rows: list[tuple[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(
        data=[(facility, "coal-facilities", mine) for facility, mine in rows],
        columns=["safeguard_facility_name", "data_source_name", "data_source_id"],
    )


def test_allocate_safeguard_facility_emissions_single_mine(domain_grid, coal_facilities_df):
    safeguard_facilities_df = pd.DataFrame({"facility_name": ["Facility 1"], "ch4_kg": [100.0]})
    facility_locations_df = facility_locations([("Facility 1", "Mine B")])

    facilities, locations, gridded = allocate_safeguard_facility_emissions(
        domain_grid=domain_grid,
        safeguard_facilities_df=safeguard_facilities_df,
        facility_locations_df=facility_locations_df,
        coal_facilities_df=coal_facilities_df,
        coal_data_source_name="coal-facilities",
    )

    assert list(facilities["facility_name"]) == ["Facility 1"]
    assert list(locations["data_source_id"]) == ["Mine B"]
    assert gridded.shape == domain_grid.shape
    assert gridded[1, 2] == 100.0
    assert gridded.sum() == 100.0


def test_allocate_safeguard_facility_emissions_splits_between_mines(
    domain_grid, coal_facilities_df
):
    safeguard_facilities_df = pd.DataFrame({"facility_name": ["Facility 1"], "ch4_kg": [100.0]})
    facility_locations_df = facility_locations([("Facility 1", "Mine A"), ("Facility 1", "Mine C")])

    facilities, locations, gridded = allocate_safeguard_facility_emissions(
        domain_grid=domain_grid,
        safeguard_facilities_df=safeguard_facilities_df,
        facility_locations_df=facility_locations_df,
        coal_facilities_df=coal_facilities_df,
        coal_data_source_name="coal-facilities",
    )

    # Mine A has repeated rows in the coal data but counts as one location
    assert len(locations) == 2
    assert gridded[0, 0] == 50.0
    assert gridded[3, 3] == 50.0
    assert gridded.sum() == 100.0


def test_allocate_safeguard_facility_emissions_mine_outside_domain(domain_grid, coal_facilities_df):
    safeguard_facilities_df = pd.DataFrame({"facility_name": ["Facility 1"], "ch4_kg": [100.0]})
    facility_locations_df = facility_locations(
        [("Facility 1", "Mine B"), ("Facility 1", "Mine Outside")]
    )

    facilities, locations, gridded = allocate_safeguard_facility_emissions(
        domain_grid=domain_grid,
        safeguard_facilities_df=safeguard_facilities_df,
        facility_locations_df=facility_locations_df,
        coal_facilities_df=coal_facilities_df,
        coal_data_source_name="coal-facilities",
    )

    # the facility is located, so all its emissions count as allocated, but
    # only the share at the mine inside the domain appears on the grid
    assert list(facilities["facility_name"]) == ["Facility 1"]
    assert gridded[1, 2] == 50.0
    assert gridded.sum() == 50.0


def test_allocate_safeguard_facility_emissions_no_location(domain_grid, coal_facilities_df, caplog):
    safeguard_facilities_df = pd.DataFrame({
        "facility_name": ["Facility 1", "Facility 2"],
        "ch4_kg": [100.0, 25.0],
    })
    facility_locations_df = facility_locations([("Facility 1", "Mine B")])

    with caplog.at_level(logging.WARNING):
        facilities, locations, gridded = allocate_safeguard_facility_emissions(
            domain_grid=domain_grid,
            safeguard_facilities_df=safeguard_facilities_df,
            facility_locations_df=facility_locations_df,
            coal_facilities_df=coal_facilities_df,
            coal_data_source_name="coal-facilities",
        )

    assert list(facilities["facility_name"]) == ["Facility 1"]
    assert gridded.sum() == 100.0
    expected_warning = "No coal mine found for Safeguard facility 'Facility 2', leaving 25.00kg CH4"
    assert expected_warning in caplog.text


def test_allocate_safeguard_facility_emissions_unknown_mine(
    domain_grid, coal_facilities_df, caplog
):
    safeguard_facilities_df = pd.DataFrame({"facility_name": ["Facility 1"], "ch4_kg": [100.0]})
    # location references a mine which isn't in the coal data
    facility_locations_df = facility_locations([("Facility 1", "Mine Z")])

    with caplog.at_level(logging.WARNING):
        facilities, locations, gridded = allocate_safeguard_facility_emissions(
            domain_grid=domain_grid,
            safeguard_facilities_df=safeguard_facilities_df,
            facility_locations_df=facility_locations_df,
            coal_facilities_df=coal_facilities_df,
            coal_data_source_name="coal-facilities",
        )

    assert len(facilities) == 0
    assert len(locations) == 0
    assert gridded.sum() == 0.0
    assert "No coal mine found for Safeguard facility 'Facility 1'" in caplog.text


def test_allocate_safeguard_facility_emissions_other_data_source(domain_grid, coal_facilities_df):
    safeguard_facilities_df = pd.DataFrame({"facility_name": ["Facility 1"], "ch4_kg": [100.0]})
    facility_locations_df = pd.DataFrame({
        "safeguard_facility_name": ["Facility 1", "Facility 1"],
        "data_source_name": ["coal-facilities", "npi-facilities"],
        "data_source_id": ["Mine B", "Mine C"],
    })

    facilities, locations, gridded = allocate_safeguard_facility_emissions(
        domain_grid=domain_grid,
        safeguard_facilities_df=safeguard_facilities_df,
        facility_locations_df=facility_locations_df,
        coal_facilities_df=coal_facilities_df,
        coal_data_source_name="coal-facilities",
    )

    # only locations from the coal data source are used
    assert list(locations["data_source_id"]) == ["Mine B"]
    assert gridded[1, 2] == 100.0
    assert gridded[3, 3] == 0.0


def test_allocate_safeguard_facility_emissions_no_facilities(domain_grid, coal_facilities_df):
    safeguard_facilities_df = pd.DataFrame({"facility_name": [], "ch4_kg": []})
    facility_locations_df = facility_locations([("Facility 1", "Mine B")])

    facilities, locations, gridded = allocate_safeguard_facility_emissions(
        domain_grid=domain_grid,
        safeguard_facilities_df=safeguard_facilities_df,
        facility_locations_df=facility_locations_df,
        coal_facilities_df=coal_facilities_df,
        coal_data_source_name="coal-facilities",
    )

    assert len(facilities) == 0
    assert len(locations) == 0
    np.testing.assert_array_equal(gridded, np.zeros(domain_grid.shape))
