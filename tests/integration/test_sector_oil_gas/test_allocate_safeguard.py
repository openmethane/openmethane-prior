
import attrs
import datetime

import numpy as np

from openmethane_prior.data_sources.safeguard import safeguard_mechanism_data_source, safeguard_locations_data_source
from openmethane_prior.lib import PriorConfig
from openmethane_prior.lib.grid.geometry import polygon_cell_intersection
from openmethane_prior.sectors.oil_gas.data import vic_oil_gas_data_source
from openmethane_prior.sectors.oil_gas.safeguard_oil_gas import allocate_safeguard_facility_emissions


def test_oil_gas_allocate_safeguard(config: PriorConfig, cache_dir, data_manager):
    # we will need to test with configs in the SGM period and outside
    config_params = attrs.asdict(config)
    del config_params["start_date"]
    del config_params["end_date"]
    del config_params["domain_path"]

    # period within safeguard period, using the full domain since test fields
    # are in Victoria, so not in au-test
    config_2023 = PriorConfig(
        **config_params,
        domain_path="https://openmethane.s3.amazonaws.com/domains/aust10km/v1/domain.aust10km.nc",
        start_date=datetime.datetime(2023, 7, 1),
        end_date=datetime.datetime(2023, 7, 2),
    )
    config_2023.prepare_paths()
    config_2023.load_cached_inputs()

    safeguard_facilities_asset = data_manager.get_asset(safeguard_mechanism_data_source)
    facility_locations_asset = data_manager.get_asset(safeguard_locations_data_source)
    oil_gas_asset = data_manager.get_asset(vic_oil_gas_data_source)

    # verify facility emissions in safeguard data
    otway_facility = safeguard_facilities_asset.data[safeguard_facilities_asset.data["facility_name"] == "Otway"]
    assert len(otway_facility) == 1
    assert otway_facility.iloc[0]["ch4_kg"] == 257750.0

    # verify facilities related to Otway lie inside the domain
    oil_gas_otway_fields = oil_gas_asset.data[oil_gas_asset.data["tag"].isin(["geographe", "thylacine"])]
    assert len(oil_gas_otway_fields) == 2
    oil_gas_otway_geometry = oil_gas_otway_fields["geometry"].union_all()
    oil_gas_otway_cells = polygon_cell_intersection(oil_gas_otway_geometry, config_2023.domain_grid())
    assert oil_gas_otway_cells == [
        ((309, 84), 0.049298356711897674),
        ((308, 85), 0.1448363451138687),
        ((309, 85), 0.40146462148077633),
        ((309, 86), 0.40120661630811183),
        ((310, 86), 0.003194060385346512),
    ]

    # run the test
    facilities, locations, gridded_emissions = allocate_safeguard_facility_emissions(
        config=config_2023,
        anzsic_codes=["070"],
        safeguard_facilities_asset=safeguard_facilities_asset,
        facility_locations_asset=facility_locations_asset,
        reference_data_asset=oil_gas_asset,
        grid=config_2023.domain_grid(),
    )

    assert len(facilities) == 2
    assert len(locations) == 34

    for cell_indexes, area_proportion in oil_gas_otway_cells:
        ix, iy = cell_indexes
        expected_emissions = (area_proportion * 257750.0
                              / config_2023.domain_grid().cell_area
                              / (365 * 24 * 60 * 60))

        # check the emissions are allocated to the right grid cell
        assert np.isclose(gridded_emissions[iy, ix], expected_emissions)
