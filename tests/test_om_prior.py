import sys
import os

# TODO With the new folder structure, the next lines will become obsolete
# insert root directory into python module search path
sys.path.insert(1, os.getcwd())

import subprocess
import pytest
import xarray as xr
import numpy as np
import pandas as pd
import requests

from omOutputs import domainOutputPath
from omDownloadInputs import download_input_files, sectoralEmissionsPath, remote, downloads
from omUtils import getenv, secsPerYear
from omInputs import sectoralEmissionsPath, livestockDataPath

@pytest.fixture
def output_domain_file(root_dir, monkeypatch):

    monkeypatch.chdir(root_dir)

    print(f"Run {os.path.join(root_dir, 'omDownloadInputs.py')}")
    subprocess.run(["python", os.path.join(root_dir, "omDownloadInputs.py")], check=True)

    print(f"Run {os.path.join(root_dir, 'omCreateDomainInfo.py')}")
    subprocess.run(["python", os.path.join(root_dir, "omCreateDomainInfo.py")], check=True)

    print(f"Run {os.path.join(root_dir, 'omPrior.py')}")
    subprocess.run(["python", os.path.join(root_dir, "omPrior.py"), "2022-07-01", "2022-07-02"], check=True)

    filepath_ds = os.path.join(root_dir, "outputs/out-om-domain-info.nc")

    out_om_domain = xr.load_dataset(filepath_ds)

    yield out_om_domain

    downloaded_files = os.listdir("inputs")

    for file in [i for i in downloaded_files if i != 'README.md'] :
        filepath = os.path.join("inputs", file)
        os.remove(filepath)

    os.remove("outputs/out-om-domain-info.nc")






@pytest.fixture
def input_files(root_dir):

    download_input_files(root_path=root_dir,
                         downloads=downloads,
                         remote=remote)

    input_folder = os.path.join(root_dir, "inputs")

    downloaded_files = os.listdir(input_folder)

    yield downloaded_files

    for file in [i for i in downloaded_files if i != 'README.md'] :
        filepath = os.path.join(input_folder, file)
        os.remove(filepath)

@pytest.fixture
def livestock_data(root_dir):

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

@pytest.fixture
def sector_data(root_dir):

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

def test_002_inputs_folder_is_empty(root_dir):
    input_folder = os.path.join(root_dir, "inputs")

    EXPECTED_FILES = ['README.md']

    assert os.listdir(input_folder) == EXPECTED_FILES, f"Folder '{input_folder}' is not empty"
def test_003_omDownloadInputs(root_dir, input_files) :

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

def test_003_agriculture_emissions(root_dir, livestock_data, sector_data) :

    lsVal = round(np.sum(livestock_data["CH4_total"].values))
    agVal = round(sector_data["agriculture"] * 1e9)
    agDX = agVal - lsVal

    assert agDX > 0, f"Livestock CH4 exceeds bounds of total agriculture CH4: {agDX / 1e9}"

# TODO Update this test when file structure is clear.
# This test ensures that the grid size for all input files is 10 km.
# When we re-arrange the files and scripts there may be other
# thing we want to test as well.
def test_004_grid_size_for_geo_files(root_dir, monkeypatch):

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

def test_005_output_domain_file(output_domain_file, num_regression, root_dir, monkeypatch):

    mean_values = {key: output_domain_file[key].mean().item() for key in output_domain_file.keys()}

    num_regression.check(mean_values)

#
# def test_002_emission_discrepancy(root_dir):
#     # Check each layer in the output sums up to the input
#     with xr.open_dataset(domainOutputPath) as dss :
#         ds = dss.load()
#
#     sectoralEmissionsFile = getenv("SECTORAL_EMISSIONS")
#
#     downloads = [
#         [sectoralEmissionsFile, sectoralEmissionsPath],
#     ]
#
#     download_input_files(root_path=root_dir,
#                          downloads=downloads,
#                          remote=remote)
#
#     sectorData = pd.read_csv(sectoralEmissionsPath).to_dict(orient="records")[0]
#
#     modelAreaM2 = ds.DX * ds.DY
#     for sector in sectorData.keys() :
#         layerName = f"OCH4_{sector.upper()}"
#         sectorVal = float(sectorData[sector]) * 1e9
#
#         if layerName in ds :
#             layerVal = np.sum(ds[layerName][0].values * modelAreaM2 * secsPerYear)
#
#             if sector == "agriculture" :
#                 layerVal += np.sum(ds["OCH4_LIVESTOCK"][0].values * modelAreaM2 * secsPerYear)
#
#             diff = round(layerVal - sectorVal)
#             perectenageDifference = diff / sectorVal * 100
#
#             assert abs(perectenageDifference) < 0.1, f"Discrepency of {perectenageDifference}% in {sector} emissions"
#
#     os.remove("outputs/out-om-domain-info.nc")