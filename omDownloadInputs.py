"""
omDownloadInputs.py

Copyright 2023 The Superpower Institute Ltd
Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

import os

import requests
from omInputs import (
    auShapefilePath,
    coalPath,
    electricityPath,
    landUsePath,
    livestockDataPath,
    ntlPath,
    oilGasPath,
    sectoralEmissionsPath,
    sectoralMappingsPath,
    termitePath,
    wetlandPath,
)
from omUtils import getenv

remote = getenv("PRIOR_REMOTE")

electricityFile = getenv("CH4_ELECTRICITY")
fugitivesFile = getenv("CH4_FUGITIVES")
landUseFile = getenv("LAND_USE")
sectoralEmissionsFile = getenv("SECTORAL_EMISSIONS")
sectoralMappingsFile = getenv("SECTORAL_MAPPING")
ntlFile = getenv("NTL")
auShapefileFile = getenv("AUSF")
livestockDataFile = getenv("LIVESTOCK_DATA")
termiteFile = getenv("TERMITES")
wetlandFile = getenv("WETLANDS")
coalFile = getenv("COAL")
oilGasFile = getenv("OILGAS")
downloads = [
    [electricityFile, electricityPath],
    [coalFile, coalPath],
    [oilGasFile, oilGasPath],
    [landUseFile, landUsePath],
    [sectoralEmissionsFile, sectoralEmissionsPath],
    [sectoralMappingsFile, sectoralMappingsPath],
    [ntlFile, ntlPath],
    [auShapefileFile, auShapefilePath],
    [livestockDataFile, livestockDataPath],
    [termiteFile, termitePath],
    [wetlandFile, wetlandPath],
]

for filename, filepath in downloads:
    url = f"{remote}{filename}"

    if not os.path.exists(filepath):
        print(f"Downloading {filename} to {filepath} from {url}")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with requests.get(url, stream=True) as response:
            with open(filepath, mode="wb") as file:
                for chunk in response.iter_content(chunk_size=10 * 1024):
                    file.write(chunk)
    else:
        print(f"Skipping {filename} because it already exists at {filepath}")
