# work around until folder structure is updated
import os
import sys

# insert root directory into python module search path
sys.path.insert(1, os.getcwd())

from omInputs import sectoralEmissionsPath, livestockDataPath
from omDownloadInputs import root_path, downloads, remote, download_input_files
from omUtils import getenv
import requests
from pathlib import Path
import pandas as pd
import xarray as xr
import numpy as np

ROOT_DIRECTORY = Path(__file__).parent.parent


def test_001_response_for_download_links() :
    for filename, filepath in downloads :
        url = f"{remote}{filename}"
        with requests.get(url, stream=True) as response :
            print(f"Response code for {url}: {response.status_code}")
            assert response.status_code == 200


def test_002_omDownloadInputs() :
    input_folder = os.path.join(ROOT_DIRECTORY, "inputs")

    EXPECTED_FILES_START = ['README.md']
    EXPECTED_FILES_END = [
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

    assert os.listdir(input_folder) == EXPECTED_FILES_START, f"Folder '{input_folder}' is not empty"

    download_input_files(root_path=root_path,
                         downloads=downloads,
                         remote=remote)

    downloaded_files = os.listdir(input_folder)

    for file in [i for i in downloaded_files if i != 'README.md'] :
        filepath = os.path.join(input_folder, file)
        os.remove(filepath)

    assert sorted(downloaded_files) == sorted(EXPECTED_FILES_END)


def test_003_agriculture_emissions(root_dir) :
    # TODO: It would be better to download the input data once
    # for all tests and clean up the folder afterwards
    sectoralEmissionsFile = getenv("SECTORAL_EMISSIONS")
    livestockDataFile = getenv("LIVESTOCK_DATA")

    downloads = [
        [sectoralEmissionsFile, sectoralEmissionsPath],
        [livestockDataFile, livestockDataPath],
    ]

    download_input_files(root_path=root_dir,
                         downloads=downloads,
                         remote=remote)

    sectorData = pd.read_csv(sectoralEmissionsPath).to_dict(orient="records")[0]

    # Load Livestock inventory and check that it doesn't exceed total agriculture inventory
    with xr.open_dataset(livestockDataPath) as lss :
        ls = lss.load()

    lsVal = round(np.sum(ls["CH4_total"].values))
    agVal = round(sectorData["agriculture"] * 1e9)
    agDX = agVal - lsVal

    assert agDX > 0, f"Livestock CH4 exceeds bounds of total agriculture CH4: {agDX / 1e9}"

    # clean up inputs directory
    input_folder = os.path.join(ROOT_DIRECTORY, "inputs")
    downloaded_files = os.listdir(input_folder)

    for file in [i for i in downloaded_files if i != 'README.md'] :
        filepath = os.path.join(input_folder, file)
        os.remove(filepath)
