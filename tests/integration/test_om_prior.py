import os
import attrs
import numpy as np
import pandas as pd
import requests
import xarray as xr

from openmethane_prior.layers.omGFASEmis import download_GFAS
from openmethane_prior.utils import SECS_PER_YEAR


def test_001_response_for_download_links(config):
    layer_info = attrs.asdict(config.layer_inputs)
    for file_fragment in layer_info.values():
        url = f"{config.remote}{file_fragment}"
        with requests.get(url, stream=True, timeout=30) as response:
            print(f"Response code for {url}: {response.status_code}")
            assert response.status_code == 200


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
        "domains/aust-test/v1.0.0/prior_domain_aust-test_v1.0.0.d01.nc",
        "domains/aust10km/v1.0.0/prior_domain_aust10km_v1.0.0.d01.nc",
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


# TODO Update this test when file structure is clear.
def test_009_output_domain_xr(output_domain):
    mean_values = {key: output_domain[key].mean().item() for key in output_domain.keys()}

    expected_values = {
        "grid_projection": 0.0,
        "lat": -26.9831600189209,
        "lat_bounds": -26.98314616858941,
        "lon": 133.302001953125,
        "lon_bounds": 133.30200195229452,
        "projection_x": 0.0,
        "projection_y": -15629.25,
        "time_bounds": 1656720000000000000,
        "land_mask": 0.39128163098043234,
        "LANDMASK": 0.39128163456916809,
        "OCH4_AGRICULTURE": 3.8221794892533713e-13,
        "OCH4_LULUCF": 8.2839841777071689e-13,
        "OCH4_WASTE": 7.680668803420382e-13,
        "OCH4_LIVESTOCK": 3.3252710482543987e-12,
        "OCH4_INDUSTRIAL": 4.640698224515257e-15,
        "OCH4_STATIONARY": 8.585292184512728e-14,
        "OCH4_TRANSPORT": 1.8562792898061028e-14,
        "OCH4_ELECTRICITY": 2.3204437472569124e-14,
        "OCH4_FUGITIVE": 1.906824649308364e-12,
        "OCH4_TERMITE": 8.106151383815985e-13,
        "OCH4_FIRE": 2.6126792244431096e-13,
        "OCH4_WETLANDS": 1.8596938045956645e-11,
        "OCH4_TOTAL": 2.701186087531425e-11,
    }

    assert mean_values == expected_values


def test_010_emission_discrepancy(config, root_dir, output_domain, input_files):
    modelAreaM2 = output_domain.DX * output_domain.DY

    filepath_sector = config.as_input_file(config.layer_inputs.sectoral_emissions_path)
    sector_data = pd.read_csv(filepath_sector).to_dict(orient="records")[0]

    for sector in sector_data.keys():
        layerName = f"OCH4_{sector.upper()}"
        sectorVal = float(sector_data[sector]) * 1e9

        # Check each layer in the output sums up to the input
        if layerName in output_domain:
            layerVal = np.sum(output_domain[layerName][0].values * modelAreaM2 * SECS_PER_YEAR)

            if sector == "agriculture":
                layerVal += np.sum(
                    output_domain["OCH4_LIVESTOCK"][0].values * modelAreaM2 * SECS_PER_YEAR
                )

            diff = round(layerVal - sectorVal)
            percentage_diff = diff / sectorVal * 100

            assert (
                abs(percentage_diff) < 0.1
            ), f"Discrepancy of {percentage_diff}% in {sector} emissions"


def test_011_output_domain_dims(output_domain):
    expected_dimensions = {
        "time": 2,
        "vertical": 1,
        "y": 430,
        "x": 454,
        "corner": 4,
        "time_period": 2,
    }

    assert output_domain.dims == expected_dimensions


def test_012_output_variable_attributes(output_domain):
    assert output_domain.variables["OCH4_TOTAL"].attrs == {
        "units": "kg/m2/s",
        "standard_name": "surface_upward_mass_flux_of_methane",
        "long_name": "total expected flux of methane based on public data",
    }

    for layer_name in [layer for layer in list(output_domain.variables.keys()) if layer.startswith("OCH4_") and layer != "OCH4_TOTAL"]:
        assert output_domain.variables[layer_name].attrs["units"] == "kg/m2/s"
        assert output_domain.variables[layer_name].attrs["long_name"] == layer_name
        assert output_domain.variables[layer_name].attrs["standard_name"].startswith("surface_upward_mass_flux_of_methane_due_to_emission_from_")
