
import datetime
import logging

import attrs
import pytest

from openmethane_prior.data_sources.safeguard import (
    safeguard_locations_data_source,
    safeguard_mechanism_data_source,
)
from openmethane_prior.lib import DataManager


def test_safeguard_data_source_2023_24(config):
    config_2023 = attrs.evolve(
        config,
        start_date=datetime.datetime(2023, 7, 1),
        end_date=datetime.datetime(2023, 7, 2),
    )
    data_manager = DataManager.from_config(config_2023)

    safeguard_asset = data_manager.get_asset(safeguard_mechanism_data_source)
    safeguard_df = safeguard_asset.data

    assert safeguard_asset.path.name == "2023-24-baselines-and-emissions-table.csv"
    assert len(safeguard_df) == 231 # 233 rows, 2 duplicates

    safeguard_row_appin = safeguard_df.loc[3]

    assert safeguard_row_appin.facility_name == "APN01 Appin Colliery - ICH Facility"
    assert safeguard_row_appin.state == "NSW"
    assert safeguard_row_appin.anzsic == "Coal mining (060)"
    assert safeguard_row_appin.anzsic_code == "060"
    assert safeguard_row_appin.co2e_ch4 == 1731355.0
    assert safeguard_row_appin.ch4_kg == 1731355.0 * 1000 * (1 / 28)
    assert safeguard_row_appin.reporting_start == datetime.date(2023, 7, 1)
    assert safeguard_row_appin.reporting_end == datetime.date(2024, 6, 30)


def test_safeguard_data_source_2024_25(config):
    config_2024 = attrs.evolve(
        config,
        start_date=datetime.datetime(2025, 6, 1),
        end_date=datetime.datetime(2025, 6, 30),
    )
    data_manager = DataManager.from_config(config_2024)

    safeguard_asset = data_manager.get_asset(safeguard_mechanism_data_source)
    safeguard_df = safeguard_asset.data

    assert safeguard_asset.path.name == "2024-25-baselines-and-emissions-table.csv"
    assert len(safeguard_df) == 227 # 228 rows, 1 duplicate

    safeguard_appin = safeguard_df[
        safeguard_df["facility_name"] == "APN01 Appin Colliery - ICH Facility"
    ]
    assert len(safeguard_appin) == 1
    safeguard_row_appin = safeguard_appin.iloc[0]

    assert safeguard_row_appin.state == "NSW"
    assert safeguard_row_appin.anzsic_code == "060"
    assert safeguard_row_appin.co2e_ch4 == 2245885.0
    assert safeguard_row_appin.ch4_kg == 2245885.0 * 1000 * (1 / 28)
    assert safeguard_row_appin.reporting_start == datetime.date(2024, 7, 1)
    assert safeguard_row_appin.reporting_end == datetime.date(2025, 6, 30)


def test_safeguard_data_source_unpublished_year(config, caplog):
    config_2025 = attrs.evolve(
        config,
        start_date=datetime.datetime(2025, 7, 1),
        end_date=datetime.datetime(2025, 7, 2),
    )
    data_manager = DataManager.from_config(config_2025)

    with caplog.at_level(logging.WARNING):
        safeguard_asset = data_manager.get_asset(safeguard_mechanism_data_source)

    assert len(safeguard_asset.data) == 0
    assert "ch4_kg" in safeguard_asset.data.columns
    assert not safeguard_asset.path.exists()
    assert "No Safeguard Mechanism data published for FY 2025-26" in caplog.text


def test_safeguard_data_source_spans_financial_years(config):
    config_span = attrs.evolve(
        config,
        start_date=datetime.datetime(2024, 6, 30),
        end_date=datetime.datetime(2024, 7, 1),
    )
    data_manager = DataManager.from_config(config_span)

    with pytest.raises(ValueError, match="must be within the same financial year"):
        data_manager.get_asset(safeguard_mechanism_data_source)


def test_safeguard_locations_data_source(data_manager):
    locations_df = data_manager.get_asset(safeguard_locations_data_source).data

    # only rows with complete data are read
    assert len(locations_df) > 0
    assert len(locations_df[locations_df["safeguard_facility_name"] == ""]) == 0
    assert len(locations_df[locations_df["data_source_name"] == ""]) == 0
    assert len(locations_df[locations_df["data_source_id"] == ""]) == 0

    # find a row with known values, check the values match expected
    locations_row_blackwater = locations_df[locations_df["safeguard_facility_name"] == "Blackwater Mine"].iloc[0]
    assert dict(locations_row_blackwater) == {
        "safeguard_facility_name": "Blackwater Mine",
        "data_source_name": "coal-facilities",
        "data_source_id": "Blackwater Coal Mine",
    }
