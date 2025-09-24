import os
import attrs
import numpy as np
import pytest
import requests

from openmethane_prior.layers.omGFASEmis import GFASDataSource


@pytest.mark.skip(reason="Duplicated by test_004_omDownloadInputs")
def test_001_response_for_download_links(config):
    layer_info = attrs.asdict(config.layer_inputs)
    for file_fragment in layer_info.values():
        url = f"{config.remote}{file_fragment}"
        with requests.get(url, stream=True, timeout=30) as response:
            assert response.status_code == 200, f"Unexpected {response.status_code} response for: {url}"


@pytest.mark.skip(reason="Duplicated by other tests")
def test_002_cdsapi_connection(root_dir, tmp_path, start_date, end_date):
    data_path = tmp_path / "sub"
    data_path.mkdir(parents=True)
    gfas_source = GFASDataSource(
        name="cdsapi-test",
        start_date=start_date,
        end_date=end_date,
    )
    gfas_source.fetch(data_path=data_path)

    assert os.path.exists(data_path / gfas_source.file_name)


def test_004_omDownloadInputs(root_dir, input_files, config):
    EXPECTED_FILES = [
        "ch4-electricity.csv",
        "coal-mining_emissions-sources.csv",
        "oil-and-gas-production-and-transport_emissions-sources.csv",
        "nasa-nighttime-lights.tiff",
        "AUS_2021_AUST_SHP_GDA2020.zip",
        "termite_emissions_2010-2016.nc",
        "DLEM_totflux_CRU_diagnostic.nc",
        "domain.au-test.nc",
        "domain.aust10km.nc",
    ]

    assert sorted([str(fn.relative_to(config.input_path)) for fn in input_files]) == sorted(
        EXPECTED_FILES
    )


def test_009_prior_emissions_ds(prior_emissions_ds):
    numeric_keys = [key for key in prior_emissions_ds.keys() if np.issubdtype(prior_emissions_ds[key].dtype, np.number)]

    result_means = {key: prior_emissions_ds[key].mean().item() for key in numeric_keys}
    expected_means = {
        "lambert_conformal": 0.0,
        "land_mask": 1.0,
        "lat": -23.267749786376953,
        "lon": 148.6399383544922,
        "x_bounds": 1530000.375,
        "y_bounds": 364369.5,

        "ch4_sector_agriculture": 1.819010994856642e-12,
        "ch4_sector_lulucf": 5.597882496026664e-12,
        "ch4_sector_waste": 3.2309244166864934e-12,
        "ch4_sector_livestock": 4.0547154335803873e-11,
        "ch4_sector_industrial": 5.645377828854301e-14,
        "ch4_sector_stationary": 8.9951585930315e-13,
        "ch4_sector_transport": 2.0972791286013642e-13,
        "ch4_sector_electricity": 2.283888848991229e-13,
        "ch4_sector_fugitive": 4.662622971875453e-10,
        "ch4_sector_termite": 2.436579367090519e-12,
        "ch4_sector_fire": 3.6974516872713414e-13,
        "ch4_sector_wetlands": 1.2524275273123607e-10,
        "ch4_total": 6.469004331105554e-10,

        # deprecated
        "OCH4_TOTAL": 6.469004331105554e-10,
        "LANDMASK": 1.0,
    }

    assert result_means == expected_means

    result_maxs = {key: prior_emissions_ds[key].max().item() for key in numeric_keys}
    expected_maxs = {
        "lambert_conformal": 0,
        "land_mask": 1,
        "lat": -22.806066513061523,
        "lon": 149.1439208984375,
        "x_bounds": 1580000.375,
        "y_bounds": 414369.5,

        "ch4_sector_agriculture": 2.3722956957857355e-12,
        "ch4_sector_lulucf": 1.3019979971763157e-10,
        "ch4_sector_waste": 1.211596656257435e-10,
        "ch4_sector_livestock": 7.545056510007907e-11,
        "ch4_sector_industrial": 5.463926537135979e-13,
        "ch4_sector_stationary": 8.706040097264147e-12,
        "ch4_sector_transport": 2.0298692902317285e-12,
        "ch4_sector_electricity": 1.284687477557566e-11,
        "ch4_sector_fugitive": 1.4772942018755247e-08,
        "ch4_sector_termite": 3.3858020553889645e-12,
        "ch4_sector_fire": 5.498670963000052e-11,
        "ch4_sector_wetlands": 2.5512281176531815e-10,
        "ch4_total": 1.4878273070171758e-08,

        # deprecated
        "OCH4_TOTAL": 1.4878273070171758e-08,
        "LANDMASK": 1.0,
    }

    assert result_maxs == expected_maxs

    # spot check an entire row and column to ensure no geometric shifting
    results_keys = [key for key in prior_emissions_ds.keys() if key.startswith("ch4")]
    result_y_band = {key: prior_emissions_ds[key][0, 0, 4].sum().item() for key in results_keys}
    expected_y_band = {
        "ch4_sector_agriculture": 1.67353386778753e-11,
        "ch4_sector_lulucf": 0.0,
        "ch4_sector_waste": 0.0,
        "ch4_sector_livestock": 4.0390212981728717e-10,
        "ch4_sector_industrial": 8.447339161268685e-13,
        "ch4_sector_stationary": 1.3459711244899672e-11,
        "ch4_sector_transport": 3.1382183181070133e-12,
        "ch4_sector_electricity": 0.0,
        "ch4_sector_fugitive": 0.0,
        "ch4_sector_termite": 2.3266076565331417e-11,
        "ch4_sector_fire": 0.0,
        "ch4_sector_wetlands": 1.118552889201041e-09,
        "ch4_total": 1.5798990988248708e-09,
    }

    assert result_y_band == expected_y_band

    result_x_band = {key: prior_emissions_ds[key][0, 0, :, 4].sum().item() for key in results_keys}
    expected_x_band = {
        "ch4_sector_agriculture": 1.9563626540336016e-11,
        "ch4_sector_lulucf": 1.3823390714122407e-11,
        "ch4_sector_waste": 0.0,
        "ch4_sector_livestock": 4.7123459295837e-10,
        "ch4_sector_industrial": 6.323611496026155e-13,
        "ch4_sector_stationary": 1.0075833719532698e-11,
        "ch4_sector_transport": 2.3492454907470443e-12,
        "ch4_sector_electricity": 1.284687477557566e-11,
        "ch4_sector_fugitive": 5.683014839736737e-09,
        "ch4_sector_termite": 2.363145790162946e-11,
        "ch4_sector_fire": 0.0,
        "ch4_sector_wetlands": 6.705475445734077e-10,
        "ch4_total": 6.907719766909539e-09,
    }

    assert result_x_band == expected_x_band


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
