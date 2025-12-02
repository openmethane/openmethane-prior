#
# Copyright 2025 The Superpower Institute Ltd.
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
import os
import pathlib
import urllib.request
import zipfile

from openmethane_prior.lib import ConfiguredDataSource, DataSource

def zip_fetch_extractall(data_source: ConfiguredDataSource) -> pathlib.Path:
    """
    Download a zip file specified by DataSource.url, and extract the contents
    to a path specified in DataSource.file_path.
    """
    # download zip file to a temporary location, it should be cleaned up afterwards
    zip_path, response = urllib.request.urlretrieve(
        url=data_source.url,
        filename=data_source.data_path / os.path.basename(data_source.url),
    )

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # WARNING: this is dangerous for untrusted zip files
        zip_ref.extractall(data_source.asset_path)

    # clean up the zip once we've extracted the contents
    os.remove(zip_path)

    return data_source.asset_path

# source: https://climatetrace.org/data - by: Country - Australia, emission type: CH4
climate_trace_data_source = DataSource(
    name="climate-trace-aus",
    url="https://downloads.climatetrace.org/v5.0.0/country_packages/ch4/AUS.zip",
    file_path='climate-trace-AUS',
    fetch=zip_fetch_extractall,
)
