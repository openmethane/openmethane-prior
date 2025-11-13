
import attrs
import datetime

from openmethane_prior.data_sources.safeguard import (
    safeguard_locations_data_source,
    safeguard_mechanism_data_source,
)
from openmethane_prior.lib import load_config_from_env
from openmethane_prior.sectors.coal.data import coal_facilities_data_source
from openmethane_prior.sectors.coal.safeguard_coal import allocate_safeguard_facility_emissions


def test_safeguard_allocate_emissions(config, input_files, data_manager):
    # period must be within safeguard period or results will be 0
    config = load_config_from_env(**{
        **attrs.asdict(config),
        "start_date": datetime.datetime(2023, 7, 1),
        "end_date": datetime.datetime(2023, 7, 2),
    })

    safeguard_facilities_asset = data_manager.get_asset(safeguard_mechanism_data_source)
    facility_locations_asset = data_manager.get_asset(safeguard_locations_data_source)
    coal_facilities_asset = data_manager.get_asset(coal_facilities_data_source)

    # verify facility emissions in safeguard data
    sgm_capcoal_facility = safeguard_facilities_asset.data[safeguard_facilities_asset.data["facility_name"] == "Capcoal Mine"]
    assert len(sgm_capcoal_facility) == 1
    assert sgm_capcoal_facility.iloc[0]["ch4_kg"] == 30736428.57142857

    # verify facility lon/lat sits inside domain
    mines_capcoal_lonlat = coal_facilities_asset.data[coal_facilities_asset.data["source_name"] == "CapCoal Mine Complex"][["lon","lat"]].drop_duplicates()
    assert len(mines_capcoal_lonlat) == 1
    capcoal_lonlat = mines_capcoal_lonlat.iloc[0]
    assert (capcoal_lonlat["lon"], capcoal_lonlat["lat"]) == (148.580506, -22.990997)
    assert config.domain_grid().lonlat_to_cell_index(capcoal_lonlat["lon"], capcoal_lonlat["lat"]) == (4, 8, True)

    # run the test
    facilities, locations, gridded_emissions = allocate_safeguard_facility_emissions(
        config=config,
        anzsic_codes=["060"],
        safeguard_facilities_asset=safeguard_facilities_asset,
        facility_locations_asset=facility_locations_asset,
        reference_data_asset=coal_facilities_asset,
    )

    # convert facility annual emissions to kg/m2/s
    expected_emissions = (sgm_capcoal_facility.iloc[0]["ch4_kg"]
                          / config.domain_grid().cell_area
                          / (365 * 24 * 60 * 60))

    # check the emissions are allocated to the right grid cell
    assert float(gridded_emissions[8, 4]) == expected_emissions

    # 9 Safeguard facilities are represented in au-test
    assert len(gridded_emissions[gridded_emissions > 0]) == 9
    # 11 Safeguard facilities are represented in au-test
    assert len(gridded_emissions[gridded_emissions > 0]) == 11
