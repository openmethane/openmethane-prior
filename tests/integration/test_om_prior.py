import os
import numpy as np
import pytest

from openmethane_prior.sectors.fire.sector import gfas_data_source
from openmethane_prior.lib.sector.config import PriorSectorConfig
from testing import dataset_metrics


@pytest.mark.skip(reason="Duplicated by other tests")
def test_002_cdsapi_connection(tmp_path, sector_config: PriorSectorConfig):
    data_path = tmp_path / "sub"
    data_path.mkdir(parents=True)

    gfas_asset = sector_config.data_manager.get_asset(gfas_data_source)

    assert os.path.exists(gfas_asset.path)


def test_009_prior_emissions_ds(prior_emissions_ds):
    assert dataset_metrics(prior_emissions_ds) == {
        'max': {
            'LANDMASK': 1.0,
            'OCH4_TOTAL': 7.994269327449818e-09,
            'ch4_sector_agriculture': 2.3277985923203306e-12,
            'ch4_sector_coal': 7.715282353069702e-09,
            'ch4_sector_electricity': 1.284687477557566e-11,
            'ch4_sector_fire': 5.498670963000052e-11,
            'ch4_sector_industrial': 5.463926537135979e-13,
            'ch4_sector_livestock': 7.545056510007907e-11,
            'ch4_sector_lulucf': 1.3240418166971984e-10,
            'ch4_sector_oil_gas': 0.0,
            'ch4_sector_stationary': 8.706040097264147e-12,
            'ch4_sector_termite': 3.3858020553889645e-12,
            'ch4_sector_transport': 2.0298692902317285e-12,
            'ch4_sector_waste': 3.5759446442430985e-12,
            'ch4_sector_wetlands': 2.5512281176531815e-10,
            'ch4_total': 7.994269327449818e-09,
            'lambert_conformal': 0,
            'land_mask': 1,
            'lat': -22.806066513061523,
            'lon': 149.1439208984375,
            'x_bounds': 1580000.375,
            'y_bounds': 414369.5,
        },
        'mean': {
            'LANDMASK': 1.0,
            'OCH4_TOTAL': 5.596197749847237e-10,
            'ch4_sector_agriculture': 1.8375328756935794e-12,
            'ch4_sector_coal': 3.8032031703707215e-10,
            'ch4_sector_electricity': 2.283888848991229e-13,
            'ch4_sector_fire': 3.6974516872713414e-13,
            'ch4_sector_industrial': 5.645377828854301e-14,
            'ch4_sector_livestock': 4.0547154335803873e-11,
            'ch4_sector_lulucf': 7.412380485305677e-12,
            'ch4_sector_oil_gas': 0.0,
            'ch4_sector_stationary': 8.9951585930315e-13,
            'ch4_sector_termite': 2.436579367090519e-12,
            'ch4_sector_transport': 2.0972791286013642e-13,
            'ch4_sector_waste': 5.922657121199834e-14,
            'ch4_sector_wetlands': 1.2524275273123607e-10,
            'ch4_total': 5.596197749847237e-10,
            'lambert_conformal': 0.0,
            'land_mask': 1.0,
            'lat': -23.267749786376953,
            'lon': 148.6399383544922,
            'x_bounds': 1530000.375,
            'y_bounds': 364369.5,
        },
        'x_band': {
            'LANDMASK': 10.0,
            'OCH4_TOTAL': 5.062977502881392e-09,
            'ch4_sector_agriculture': 4.2241433895661604e-11,
            'ch4_sector_coal': 2.72935756932487e-09,
            'ch4_sector_electricity': 0.0,
            'ch4_sector_fire': 0.0,
            'ch4_sector_industrial': 1.0547281076660498e-12,
            'ch4_sector_livestock': 8.812359129868445e-10,
            'ch4_sector_lulucf': 4.0341018755540166e-11,
            'ch4_sector_oil_gas': 0.0,
            'ch4_sector_stationary': 1.6805689341982532e-11,
            'ch4_sector_termite': 4.7307820855158056e-11,
            'ch4_sector_transport': 3.9183546498005505e-12,
            'ch4_sector_waste': 0.0,
            'ch4_sector_wetlands': 1.3007149732291445e-09,
            'ch4_total': 5.062977502881392e-09,
            'land_mask': 10,
            'lat': -232.6233367919922,
            'lon': 1486.8963623046875,
        },
        'y_band': {
            'LANDMASK': 10.0,
            'OCH4_TOTAL': 1.8817588608227616e-08,
            'ch4_sector_agriculture': 4.089383399587878e-11,
            'ch4_sector_coal': 1.5430564706139404e-08,
            'ch4_sector_electricity': 0.0,
            'ch4_sector_fire': 0.0,
            'ch4_sector_industrial': 3.778536261999508e-13,
            'ch4_sector_livestock': 1.0031707194660715e-09,
            'ch4_sector_lulucf': 0.0,
            'ch4_sector_oil_gas': 0.0,
            'ch4_sector_stationary': 6.020594893132918e-12,
            'ch4_sector_termite': 4.639714307197451e-11,
            'ch4_sector_transport': 1.403740454438857e-12,
            'ch4_sector_waste': 0.0,
            'ch4_sector_wetlands': 2.288760014845792e-09,
            'ch4_total': 1.8817588608227616e-08,
            'land_mask': 10,
            'lat': -232.2213897705078,
            'lon': 1486.336669921875,
        },
    }


def test_011_output_dims(prior_emissions_ds):
    expected_dimensions = {
        "time": 2,
        "vertical": 1,
        "y": 10,
        "x": 10,
        "cell_bounds": 2,
        "time_period": 2,
    }

    assert prior_emissions_ds.sizes == expected_dimensions


def test_012_output_variable_attributes(prior_emissions_ds):
    assert prior_emissions_ds.variables["ch4_total"].attrs == {
        "units": "kg/m2/s",
        "standard_name": "surface_upward_mass_flux_of_methane",
        "long_name": "total expected flux of methane based on public data",
        "grid_mapping": "lambert_conformal",
    }

    for layer_name in [layer for layer in list(prior_emissions_ds.variables.keys()) if layer.startswith("ch4_sector_")]:
        assert prior_emissions_ds.variables[layer_name].attrs["units"] == "kg/m2/s"
        assert prior_emissions_ds.variables[layer_name].attrs["long_name"] == f"expected flux of methane caused by sector: {layer_name.replace('ch4_sector_', '')}"
        assert prior_emissions_ds.variables[layer_name].attrs["standard_name"].startswith("surface_upward_mass_flux_of_methane_due_to_emission_from_")
        assert prior_emissions_ds.variables[layer_name].attrs["grid_mapping"] == "lambert_conformal"

    # TODO: remove when OCH4_TOTAL layer is removed
    assert prior_emissions_ds.variables["OCH4_TOTAL"].attrs["deprecated"] == "This variable is deprecated and will be removed in future versions"
    assert prior_emissions_ds.variables["OCH4_TOTAL"].attrs["superseded_by"] == "ch4_total"
