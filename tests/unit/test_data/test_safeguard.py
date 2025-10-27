
from openmethane_prior.data_sources.safeguard import safeguard_mechanism_data_source
from openmethane_prior.data_sources.safeguard.data import (
    create_facility_from_safeguard_record,
    SafeguardFacilityRecord,
    parse_anzsic_code,
)


def test_parse_anzsic_code():
    assert parse_anzsic_code("Coal mining (060)") == "060"
    assert parse_anzsic_code("Oil and gas extraction (070)") == "070"
    assert parse_anzsic_code("Cement, lime, plaster and concrete product manufacturing (203)") == "203"
    assert parse_anzsic_code("Waste treatment, disposal and remediation services (292)") == "292"


def test_safeguard_data_source(data_manager):
    safeguard_asset = data_manager.get_asset(safeguard_mechanism_data_source)

    assert safeguard_asset.data.shape == (233, 5) # 233 rows, 5 columns
    assert list(safeguard_asset.data.columns) == [
        "facility_name", "business_name", "state", "anzsic", "co2e_ch4"
    ]

    safeguard_row_appin = safeguard_asset.data.loc[4]
    assert safeguard_row_appin.facility_name == "APN01 Appin Colliery - ICH Facility"
    assert safeguard_row_appin.business_name == "ENDEAVOUR COAL PTY LIMITED"
    assert safeguard_row_appin.state == "NSW"
    assert safeguard_row_appin.anzsic == "Coal mining (060)"
    assert safeguard_row_appin.co2e_ch4 == 1731355.0


def test_safeguard_create_facility_from_safeguard_row():
    safeguard_facility_appin = create_facility_from_safeguard_record(SafeguardFacilityRecord(
        facility_name="APN01 Appin Colliery - ICH Facility",
        business_name="ENDEAVOUR COAL PTY LIMITED",
        state="NSW",
        anzsic="Coal mining (060)",
        co2e_ch4=1731355.0, # CO2e (aka GWP)
    ))

    assert safeguard_facility_appin.name == "APN01 Appin Colliery - ICH Facility"
    assert safeguard_facility_appin.state == "NSW"
    assert safeguard_facility_appin.anzsic == "Coal mining (060)"
    assert safeguard_facility_appin.anzsic_code == "060"
    assert safeguard_facility_appin.ch4_emissions["2023-2024"] == 1731355.0 * 1000 * (1 / 28) # tCO2e to kg
