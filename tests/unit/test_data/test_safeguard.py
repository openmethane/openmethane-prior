
from openmethane_prior.data_sources.safeguard import safeguard_mechanism_data_source
from openmethane_prior.data_sources.safeguard.facility import (
    create_facility_from_safeguard_record,
    create_facility_list,
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

    assert len(safeguard_asset.data) == 231 # 233 rows, 2 duplicates

    safeguard_row_appin = safeguard_asset.data[4]
    assert safeguard_row_appin.name == "APN01 Appin Colliery - ICH Facility"
    assert safeguard_row_appin.state == "NSW"
    assert safeguard_row_appin.anzsic == "Coal mining (060)"
    assert safeguard_row_appin.anzsic_code == "060"
    assert safeguard_row_appin.ch4_emissions["2023-2024"] == 1731355.0 * 1000 / 28


def test_safeguard_create_facility_from_safeguard_row():
    safeguard_facility_appin = create_facility_from_safeguard_record(SafeguardFacilityRecord(
        facility_name="APN01 Appin Colliery - ICH Facility",
        business_name="ENDEAVOUR COAL PTY LIMITED",
        state="NSW",
        anzsic="Coal mining (060)",
        co2e_ch4=1731355.0, # CO2e (aka GWP)
    ), 28)

    assert safeguard_facility_appin.name == "APN01 Appin Colliery - ICH Facility"
    assert safeguard_facility_appin.state == "NSW"
    assert safeguard_facility_appin.anzsic == "Coal mining (060)"
    assert safeguard_facility_appin.anzsic_code == "060"
    assert safeguard_facility_appin.ch4_emissions["2023-2024"] == 1731355.0 * 1000 * (1 / 28) # tCO2e to kg

def test_safeguard_create_facility_list():
    test_records = [
        SafeguardFacilityRecord(
            facility_name="Test Coal Mine",
            business_name="DIG N DIG",
            state="NSW",
            anzsic="Coal mining (060)",
            co2e_ch4=123456.0, # CO2e (aka GWP)
        ),
        SafeguardFacilityRecord(
            facility_name="Test Coal Mine",
            business_name="Down 2 Dig", # facility has changed ownership
            state="NSW",
            anzsic="Coal mining (060)",
            co2e_ch4=111111.0, # CO2e (aka GWP)
        ),
        SafeguardFacilityRecord(
            facility_name="Dumpster Pyre",
            business_name="Global Rise",
            state="NSW",
            anzsic="Waste Burning (666)",
            co2e_ch4=222222.0, # CO2e (aka GWP)
        ),
    ]

    test_facility_list = create_facility_list(test_records, 28)

    assert len(test_facility_list) == 2 # de-duplicated matching record

    assert test_facility_list[0].name == "Test Coal Mine"
    assert test_facility_list[0].state == "NSW"
    assert test_facility_list[0].anzsic == "Coal mining (060)"
    assert test_facility_list[0].anzsic_code == "060"
    assert test_facility_list[0].ch4_emissions["2023-2024"] == (123456.0 + 111111.0) * 1000 / 28 # kg

    assert test_facility_list[1].name == "Dumpster Pyre"
    assert test_facility_list[1].state == "NSW"
    assert test_facility_list[1].anzsic == "Waste Burning (666)"
    assert test_facility_list[1].anzsic_code == "666"
    assert test_facility_list[1].ch4_emissions["2023-2024"] == 222222.0 * 1000 / 28 # kg
