import sys
import os
import subprocess
import pytest
import xarray as xr
import numpy as np
import pandas as pd
import requests
import datetime
from pathlib import Path

from openmethane_prior.omUtils import getenv, secsPerYear
from openmethane_prior.omInputs import sectoralEmissionsPath, livestockDataPath
from openmethane_prior.layers.omGFASEmis import downloadGFAS

# TODO Why can I not access my pytest fixture `root_dir` here?
root_path = Path(__file__).parent.parent
# TODO: This seems messy. Is there another way?
# insert scripts directory into python module search path
sys.path.insert(1, os.path.join(root_path, "scripts"))
from omDownloadInputs import download_input_files, sectoralEmissionsPath, remote, downloads


@pytest.fixture(scope="session")
def output_domain_file(root_dir,
                       # monkeypatch,
                       ) :

    # monkeypatch.chdir(root_dir)

    subprocess.run(["python", os.path.join(root_dir, "scripts/omDownloadInputs.py")], check=True)

    subprocess.run(["python", os.path.join(root_dir, "scripts/omCreateDomainInfo.py")], check=True)

    subprocess.run(["python", os.path.join(root_dir, "scripts/omPrior.py"), "2022-07-01", "2022-07-02"], check=True)

    filepath_ds = os.path.join(root_dir, "outputs/out-om-domain-info.nc")

    out_om_domain = xr.load_dataset(filepath_ds)

    yield out_om_domain

    downloaded_files = os.listdir("inputs")

    for file in [i for i in downloaded_files if i != 'README.md'] :
        filepath = os.path.join("inputs", file)
        os.remove(filepath)

    os.remove("outputs/out-om-domain-info.nc")


# Fixture to download and later remove all input files
@pytest.fixture(scope="session")
def input_files(root_dir) :
    download_input_files(root_path=root_dir,
                         downloads=downloads,
                         remote=remote)

    input_folder = os.path.join(root_dir, "inputs")

    downloaded_files = os.listdir(input_folder)

    yield downloaded_files

    for file in [i for i in downloaded_files if i != 'README.md'] :
        filepath = os.path.join(input_folder, file)
        os.remove(filepath)


# Fixture to download and later remove only input file for agriculture
@pytest.fixture(scope="session")
def livestock_data(root_dir) :
    livestockDataFile = getenv("LIVESTOCK_DATA")

    download_input_files(root_path=root_dir,
                         downloads=[
                             [livestockDataFile, livestockDataPath],
                         ],
                         remote=remote)

    filepath = os.path.join(root_dir, livestockDataPath)

    livestock_data_xr = xr.open_dataset(filepath)

    yield livestock_data_xr

    os.remove(filepath)


# Fixture to download and later remove only input file for sectoral emissions file
@pytest.fixture(scope="session")
def sector_data(root_dir) :
    sectoralEmissionsFile = getenv("SECTORAL_EMISSIONS")

    download_input_files(root_path=root_dir,
                         downloads=[
                             [sectoralEmissionsFile, sectoralEmissionsPath],
                         ],
                         remote=remote)

    filepath = os.path.join(root_dir, sectoralEmissionsPath)

    sector_data_pd = pd.read_csv(filepath).to_dict(orient="records")[0]

    yield sector_data_pd

    os.remove(filepath)


def test_001_response_for_download_links() :
    for filename, filepath in downloads :
        url = f"{remote}{filename}"
        with requests.get(url, stream=True) as response :
            print(f"Response code for {url}: {response.status_code}")
            assert response.status_code == 200


def test_002_cdsapi_connection(root_dir) :
    # TODO use a temporary directory instead
    filepath = os.path.join(root_dir, "tests/test_download_cdsapi.nc")
    startDate = datetime.datetime.strptime("2022-07-01", "%Y-%m-%d")
    endDate = datetime.datetime.strptime("2022-07-02", "%Y-%m-%d")

    downloadGFAS(startDate=startDate, endDate=endDate, fileName=filepath)

    assert os.path.exists(filepath)

    os.remove(filepath)


def test_003_inputs_folder_is_empty(root_dir) :
    input_folder = os.path.join(root_dir, "inputs")

    EXPECTED_FILES = ['README.md']

    assert os.listdir(input_folder) == EXPECTED_FILES, f"Folder '{input_folder}' is not empty"


def test_004_omDownloadInputs(root_dir, input_files) :
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
        'README.md',
    ]

    assert sorted(input_files) == sorted(EXPECTED_FILES)


def test_005_agriculture_emissions(root_dir, livestock_data, sector_data) :
    lsVal = round(np.sum(livestock_data["CH4_total"].values))
    agVal = round(sector_data["agriculture"] * 1e9)
    agDX = agVal - lsVal

    assert agDX > 0, f"Livestock CH4 exceeds bounds of total agriculture CH4: {agDX / 1e9}"


# TODO Update this test when file structure is clear.
# This test ensures that the grid size for all input files is 10 km.
# When we re-arrange the files and scripts there may be other
# thing we want to test as well.
def test_006_grid_size_for_geo_files(root_dir, monkeypatch) :
    expected_cell_size = 10000

    monkeypatch.chdir(root_dir)

    cmaqExamplePath = getenv("CMAQ_EXAMPLE")

    croFilePath = os.path.join(cmaqExamplePath, getenv("CROFILE"))
    dotFilePath = os.path.join(cmaqExamplePath, getenv("DOTFILE"))
    geomFilePath = os.path.join(cmaqExamplePath, getenv("GEO_EM"))

    with xr.open_dataset(geomFilePath) as geomXr :
        assert geomXr.DX == expected_cell_size
        assert geomXr.DY == expected_cell_size

    with xr.open_dataset(dotFilePath) as dotXr :
        assert dotXr.XCELL == expected_cell_size
        assert dotXr.YCELL == expected_cell_size

    with xr.open_dataset(croFilePath) as croXr :
        assert croXr.XCELL == expected_cell_size
        assert croXr.YCELL == expected_cell_size


def test_007_output_domain_file(output_domain_file, num_regression, root_dir, monkeypatch) :
    mean_values = {key : output_domain_file[key].mean().item() for key in output_domain_file.keys()}

    num_regression.check(mean_values)


def test_008_emission_discrepancy(root_dir, output_domain_file, sector_data) :
    modelAreaM2 = output_domain_file.DX * output_domain_file.DY
    for sector in sector_data.keys() :

        layerName = f"OCH4_{sector.upper()}"
        sectorVal = float(sector_data[sector]) * 1e9

        # Check each layer in the output sums up to the input
        if layerName in output_domain_file :
            layerVal = np.sum(output_domain_file[layerName][0].values * modelAreaM2 * secsPerYear)

            if sector == "agriculture" :
                layerVal += np.sum(output_domain_file["OCH4_LIVESTOCK"][0].values * modelAreaM2 * secsPerYear)

            diff = round(layerVal - sectorVal)
            perectenageDifference = diff / sectorVal * 100

            assert abs(perectenageDifference) < 0.1, f"Discrepency of {perectenageDifference}% in {sector} emissions"
