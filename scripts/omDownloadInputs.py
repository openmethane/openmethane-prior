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

import pathlib
from collections.abc import Iterable

import attrs

from openmethane_prior.config import load_config_from_env, PublishedInputDomain
from openmethane_prior.inputs import download_input_file


def download_input_files(
    remote: str, download_path: pathlib.Path, fragments: Iterable[str]
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
    downloaded_files = []
    for url_fragment in fragments:
        save_path = download_path / url_fragment

        if not save_path.resolve().is_relative_to(download_path.resolve()):
            raise ValueError(f"Check download fragment: {url_fragment}")

        download_input_file(remote, url_fragment, save_path)
        downloaded_files.append(save_path)
    return downloaded_files


if __name__ == "__main__":
    config = load_config_from_env()

    layer_fragments = [str(frag) for frag in attrs.asdict(config.layer_inputs).values()]

    # Add the input domain if it is specified
    if type(config.input_domain) == PublishedInputDomain:
        layer_fragments.append(str(config.input_domain.path))

    download_input_files(
        remote=config.remote,
        download_path=config.input_path,
        fragments=layer_fragments,
    )
