import os
import attrs
import numpy as np
import pandas as pd
import pytest
import requests
import xarray as xr

from openmethane_prior.layers.omGFASEmis import download_GFAS
from openmethane_prior.outputs import SECTOR_PREFIX
from openmethane_prior.utils import SECS_PER_YEAR

@pytest.mark.skip(reason="Duplicated by test_004_omDownloadInputs")
def test_001_response_for_download_links(config):
    layer_info = attrs.asdict(config.layer_inputs)
    for file_fragment in layer_info.values():
        url = f"{config.remote}{file_fragment}"
        with requests.get(url, stream=True, timeout=30) as response:
            assert response.status_code == 200, f"Unexpected {response.status_code} response for: {url}"


@pytest.mark.skip(reason="Duplicated by other tests")
def test_002_cdsapi_connection(root_dir, tmp_path, start_date, end_date):
    filepath = tmp_path / "sub" / "test_download_cdsapi.nc"
    filepath.parent.mkdir(parents=True)

    download_GFAS(start_date=start_date, end_date=end_date, file_name=filepath)

    assert os.path.exists(filepath)


def test_004_omDownloadInputs(root_dir, input_files, config):
    EXPECTED_FILES = [
        "ch4-electricity.csv",
        "coal-mining_emissions-sources.csv",
        "oil-and-gas-production-and-transport_emissions-sources.csv",
        "NLUM_ALUMV8_250m_2015_16_alb.tif",
        "ch4-sectoral-emissions.csv",
        "landuse-sector-map.csv",
        "nasa-nighttime-lights.tiff",
        "AUS_2021_AUST_SHP_GDA2020.zip",
        "EntericFermentation.nc",
        "termite_emissions_2010-2016.nc",
        "DLEM_totflux_CRU_diagnostic.nc",
        "domains/au-test/v1/domain.au-test.nc",
        "domains/aust10km/v1/domain.aust10km.nc",
    ]

    assert sorted([str(fn.relative_to(config.input_path)) for fn in input_files]) == sorted(
        EXPECTED_FILES
    )


def test_005_agriculture_emissions(config, root_dir, input_files):
    filepath_livestock = config.as_input_file(config.layer_inputs.livestock_path)
    livestock_data = xr.open_dataset(filepath_livestock)

    filepath_sector = config.as_input_file(config.layer_inputs.sectoral_emissions_path)
    sector_data = pd.read_csv(filepath_sector).to_dict(orient="records")[0]

    lsVal = round(np.sum(livestock_data["CH4_total"].values))
    agVal = round(sector_data["agriculture"] * 1e9)
    agDX = agVal - lsVal

    assert agDX > 0, f"Livestock CH4 exceeds bounds of total agriculture CH4: {agDX / 1e9}"


def test_009_prior_emissions_ds(prior_emissions_ds):
    numeric_keys = [key for key in prior_emissions_ds.keys() if np.issubdtype(prior_emissions_ds[key].dtype, np.number)]
    mean_values = {key: prior_emissions_ds[key].mean().item() for key in numeric_keys}

    expected_values = {
        "lambert_conformal": 0.0,
        "land_mask": 1.0,
        "lat": -23.267749786376953,
        "lon": 148.6399383544922,
        "x_bounds": 1530000.375,
        "y_bounds": 364369.5,

        "ch4_sector_agriculture": 1.1536221820595755e-12,
        "ch4_sector_lulucf": 4.592490774534104e-12,
        "ch4_sector_waste": 3.135222506646578e-12,
        "ch4_sector_livestock": 4.0547154335803873e-11,
        "ch4_sector_industrial": 5.381263572370136e-14,
        "ch4_sector_stationary": 9.95533760888496e-13,
        "ch4_sector_transport": 2.1525054289480922e-13,
        "ch4_sector_electricity": 2.885175186945258e-13,
        "ch4_sector_fugitive": 4.783832961493577e-10,
        "ch4_sector_termite": 2.436579367090519e-12,
        "ch4_sector_fire": 3.6974516872713414e-13,
        "ch4_sector_wetlands": 1.2524275273123607e-10,
        "ch4_total": 6.574139776508888e-10,

        # deprecated
        "OCH4_TOTAL": 6.574139776508888e-10,
        "LANDMASK": 1.0,
    }

    assert mean_values == expected_values


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
