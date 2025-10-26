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
import os
import pathlib
import urllib.request
import zipfile

from openmethane_prior.lib import ConfiguredDataSource, DataSource
from openmethane_prior.lib.data_manager.parsers import parse_csv

alum_sector_mapping_data_source = DataSource(
    name="alum-sector-mapping",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/landuse-sector-map.csv",
    parse=parse_csv,
)

# filename of the GeoTIFF file inside the official zip file source
NLUM_GEOTIFF_FILENAME="NLUM_v7_250_ALUMV8_2020_21_alb.tif"

def landuse_fetch(data_source: ConfiguredDataSource) -> pathlib.Path:
    """
    Download land use of Australia official source zip file, and extract
    the GeoTIFF file we will actually use.
    """
    # download zip file to a temporary location, it should be cleaned up afterwards
    zip_path, response = urllib.request.urlretrieve(
        url=data_source.url,
        filename=data_source.data_path / os.path.basename(data_source.url),
    )

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extract(NLUM_GEOTIFF_FILENAME, data_source.data_path)

    # clean up the zip once we've extracted the geotiff
    os.remove(zip_path)

    return data_source.asset_path

# source: https://www.agriculture.gov.au/abares/aclump/land-use/land-use-of-australia-2010-11-to-2020-21
landuse_map_data_source = DataSource(
    name="landuse-map",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/NLUM_v7_250_ALUMV8_2020_21_alb_package_20241128.zip",
    # if extracted GeoTIFF already exists, it doesn't need to be refetched
    file_path=NLUM_GEOTIFF_FILENAME,
    fetch=landuse_fetch,
)

# Note: this file should be obtainable directly from the agriculture.gov.au web
# server, however their web host appears to block connections from GitHub. The
# dataset has been mirrored in our public data store while we investigate this
# behaviour with the department.
# See: https://github.com/openmethane/openmethane-prior/pull/136#issuecomment-3449011688