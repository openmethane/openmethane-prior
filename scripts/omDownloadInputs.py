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

"""Download required input files

This downloads the input files that rarely change and can be cached between runs.
"""

import os
import pathlib
from collections.abc import Iterable

import attrs
import requests

from openmethane_prior.config import load_config_from_env


def download_input_files(
    download_path: pathlib.Path, fragments: Iterable[str], remote: str
) -> list[pathlib.Path]:
    """
    Download input files from a remote location

    Parameters
    ----------
    download_path
        Path to download the files to
    fragments
        Collection of path fragments to download.

        This fragments are combined with the remote URL
        to create the full URL to download the file from.
    remote
        URL prefix to download the files from

    Returns
    -------
        List of input files that have been fetched or found locally.

    """
    download_path.mkdir(parents=True, exist_ok=True)

    downloads = []
    for fragment in fragments:
        filepath = download_path / fragment

        print(filepath)
        url = f"{remote}{fragment}"

        if not os.path.exists(filepath):
            print(f"Downloading {fragment} to {filepath} from {url}")

            with requests.get(url, stream=True, timeout=30) as response:
                with open(filepath, mode="wb") as file:
                    for chunk in response.iter_content(chunk_size=10 * 1024):
                        file.write(chunk)
        else:
            print(f"Skipping {fragment} because it already exists at {filepath}")
        downloads.append(filepath)
    return downloads


if __name__ == "__main__":
    config = load_config_from_env()

    fragments = [str(frag) for frag in attrs.asdict(config.layer_inputs).values()]
    download_input_files(download_path=config.input_path, fragments=fragments, remote=config.remote)
