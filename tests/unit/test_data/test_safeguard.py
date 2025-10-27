
from openmethane_prior.data_sources.safeguard import safeguard_mechanism_data_source


def test_safeguard_data_source(data_manager):
    safeguard_asset = data_manager.get_asset(safeguard_mechanism_data_source)

    assert safeguard_asset.data.shape == (233, 5) # 233 rows, 5 columns
    assert list(safeguard_asset.data.columns) == [
        "facility_name", "business_name", "state", "anzsic", "co2e_ch4"
    ]

    safeguard_facility_appin = safeguard_asset.data.loc[4]
    assert safeguard_facility_appin.facility_name == "APN01 Appin Colliery - ICH Facility"
    assert safeguard_facility_appin.business_name == "ENDEAVOUR COAL PTY LIMITED"
    assert safeguard_facility_appin.state == "NSW"
    assert safeguard_facility_appin.anzsic == "Coal mining (060)"
    assert safeguard_facility_appin.co2e_ch4 == 1731355.0
