
import datetime

from openmethane_prior.data_sources.safeguard import (
    safeguard_mechanism_data_source,
    safeguard_locations_data_source,
)


def test_safeguard_data_source(data_manager):
    safeguard_df = data_manager.get_asset(safeguard_mechanism_data_source).data

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


def test_safeguard_locations_data_source(data_manager):
    locations_df = data_manager.get_asset(safeguard_locations_data_source).data

    assert len(locations_df) == 65 # 72 rows, only 65 with complete data

    locations_row_appin = locations_df.iloc[5]

    assert locations_row_appin.safeguard_facility_name == "Blackwater Mine"
    assert locations_row_appin.data_source_name == "coal-facilities"
    assert locations_row_appin.data_source_id == "Blackwater Coal Mine"
