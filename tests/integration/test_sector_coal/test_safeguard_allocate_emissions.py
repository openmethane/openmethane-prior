import attrs
import datetime
import pytest

from openmethane_prior.data_sources.safeguard import (
    get_sector_safeguard_facilities,
    safeguard_locations_data_source,
    safeguard_mechanism_data_source,
)
from openmethane_prior.lib import PriorConfig
from openmethane_prior.sectors.coal.data import coal_facilities_data_source
from openmethane_prior.sectors.coal.safeguard_coal import allocate_safeguard_facility_emissions


def test_safeguard_allocate_emissions(config, input_files, data_manager):
    # we will need to test with configs in the SGM period and outside
    config_params = attrs.asdict(config)
    del config_params["start_date"]
    del config_params["end_date"]

    # period within safeguard period will yield results
    config_2023 =  PriorConfig(
        **config_params,
        start_date=datetime.datetime(2023, 7, 1),
        end_date=datetime.datetime(2023, 7, 2),
    )
    config_2023.prepare_paths()

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
    assert config.domain().grid.lonlat_to_cell_index(capcoal_lonlat["lon"], capcoal_lonlat["lat"]) == (4, 8, True)

    sector_facilities_2023 = get_sector_safeguard_facilities(
        safeguard_facilities_df=safeguard_facilities_asset.data,
        anzsic_codes=["06"],
        period=(config_2023.start_date.date(), config_2023.end_date.date()),
    )

    # run the test
    facilities, locations, gridded_emissions = allocate_safeguard_facility_emissions(
        domain_grid=config_2023.domain().grid,
        safeguard_facilities_df=sector_facilities_2023,
        facility_locations_df=facility_locations_asset.data,
        coal_facilities_df=coal_facilities_asset.data,
        coal_data_source_name=coal_facilities_asset.name,
    )

    # annual emissions scaled to the 2 day period, in a 366 day reporting year
    expected_emissions = sgm_capcoal_facility.iloc[0]["ch4_kg"] * 2 / 366

    # check the emissions are allocated to the right grid cell
    assert float(gridded_emissions[8, 4]) == pytest.approx(expected_emissions)

    # 11 Safeguard facilities are represented in au-test
    assert len(gridded_emissions[gridded_emissions > 0]) == 11

    # 69 facilities with locations, including ones located outside the domain.
    # Norwich Park Mine has no coal mine location, so isn't allocated.
    assert len(facilities) == 69
    assert "Norwich Park Mine" in set(sector_facilities_2023["facility_name"])
    assert "Norwich Park Mine" not in set(facilities["facility_name"])
    # Some facilities have multiple locations
    assert len(locations) == 72
    assert len(locations[locations["safeguard_facility_name"] == "Hunter Valley Operations mine"]) == 2
    assert len(locations[locations["safeguard_facility_name"] == "Mt Owen Glendell Complex"]) == 2

    # period outside safeguard period will allocate no emissions
    config_2022 = PriorConfig(
        **config_params,
        start_date=datetime.datetime(2022, 7, 1),
        end_date=datetime.datetime(2022, 7, 2),
    )
    config_2022.prepare_paths()

    sector_facilities_2022 = get_sector_safeguard_facilities(
        safeguard_facilities_df=safeguard_facilities_asset.data,
        anzsic_codes=["06"],
        period=(config_2022.start_date.date(), config_2022.end_date.date()),
    )

    # run the test
    facilities, locations, gridded_emissions = allocate_safeguard_facility_emissions(
        domain_grid=config_2022.domain().grid,
        safeguard_facilities_df=sector_facilities_2022,
        facility_locations_df=facility_locations_asset.data,
        coal_facilities_df=coal_facilities_asset.data,
        coal_data_source_name=coal_facilities_asset.name,
    )

    # zero emissions have been allocated, as the time period in the config is
    # outside the available Safeguard reporting period
    assert float(gridded_emissions.sum()) == 0
    assert len(gridded_emissions[gridded_emissions > 0]) == 0

