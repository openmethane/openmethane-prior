#
# Copyright 2023 The Superpower Institute Ltd.
#
# This file is part of OpenMethane.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Input file definitions and checks"""

import os
import pathlib
import sys
import urllib.parse
import requests

from openmethane_prior.config import PriorConfig


def download_input_file(remote_url: str, url_fragment: str, save_path: pathlib.Path) -> bool:
    """
    Download an input file

    Parameters
    ----------
    remote_url
        Remote URL to download the file from.
    url_fragment
        URL fragment to download.

        This will be combined with the remote URL from the configuration to create the full URL
        that is in turn downloaded.
    save_path
        Path to save the downloaded file to.

        If an existing file is found at this location, the download is skipped.

    Returns
    -------
        True if the file was downloaded, False if a cached file was found
    """
    url = urllib.parse.urljoin(remote_url, url_fragment)

    if not os.path.exists(save_path):
        print(f"Downloading {url_fragment} to {save_path} from {url}")

        save_path.parent.mkdir(parents=True, exist_ok=True)

        with requests.get(url, stream=True, timeout=30) as response:
            response.raise_for_status()

            with open(save_path, mode="wb") as file:
                for chunk in response.iter_content(chunk_size=10 * 1024):
                    file.write(chunk)

        return True
    else:
        print(f"Skipping {url_fragment} because it already exists at {save_path}")

    return False


def check_input_files(config: PriorConfig):
    """
    Check that all required input files are present

    Exits with an error code of 1 if all required files are not available
    """
    print("### Checking input files...")

    errors = []

    if not config.input_domain_file.exists():
        errors.append(
            f"Missing file for domain info at {config.input_domain_file}, "
            f"either specify an input domain to download or copy the domain file to this location."
        )

    checks = (
        (config.layer_inputs.electricity_path, "electricity facilities"),
        (config.layer_inputs.coal_path, "Coal facilities"),
        (config.layer_inputs.oil_gas_path, "Oilgas facilities"),
        (config.layer_inputs.land_use_path, "land use"),
        (config.layer_inputs.sectoral_emissions_path, "sectoral emissions"),
        (config.layer_inputs.sectoral_mapping_path, "sectoral emissions mappings"),
        (config.layer_inputs.ntl_path, "night time lights"),
        (config.layer_inputs.livestock_path, "livestock data"),
        (config.layer_inputs.termite_path, "termite data"),
        (config.layer_inputs.wetland_path, "wetlands data"),
    )

    for path, desc in checks:
        if not os.path.exists(config.as_input_file(path)):
            errors.append(f"Missing file for {desc} at {path}")

    ## Print all errors and exit (if we have any errors)
    if len(errors) > 0:
        print(
            "Some required files are missing. "
            "Suggest running omDownloadInputs.py if you're using the default input file set. "
            "See issues below."
        )
        print("\n".join(errors))
        sys.exit(1)
