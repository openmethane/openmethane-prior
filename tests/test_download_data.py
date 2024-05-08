# work around until folder structure is updated^
import os
import sys
# insert root directory into python module search path
sys.path.insert(1, os.getcwd())

from temporary_file_for_tests import downloads, remote
from definitions import ROOT_DIRECTORY
import pytest
import requests
from pathlib import Path
import subprocess

def test_001_response_for_download_links() :
    for filename, filepath in downloads :
        url = f"{remote}{filename}"
        with requests.get(url, stream=True) as response :
            print(f"Response code for {url}: {response.status_code}")
            assert response.status_code == 200


def test_002_omDownloadInputs():
    # Check if the folder is empty before running the script
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

    script_path = os.path.join(ROOT_DIRECTORY, "omDownloadInputs.py")

    subprocess.run(["python", script_path], capture_output=True, timeout=60*10, check=True)

    downloaded_files = os.listdir(input_folder)

    # clean up folder
    for file in [i for i in downloaded_files if i != 'README.md']:
        filepath = os.path.join(input_folder, file)
        os.remove(filepath)

    assert sorted(downloaded_files) == sorted(EXPECTED_FILES_END)

