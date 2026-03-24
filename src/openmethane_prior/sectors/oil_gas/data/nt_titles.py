#
# Copyright 2026 The Superpower Institute Ltd.
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
import geopandas as gpd
import numpy as np
import os
import pathlib
import shutil
import urllib
import zipfile

from openmethane_prior.lib import DataSource
from openmethane_prior.lib.data_manager.parsers import parse_geo
from openmethane_prior.lib.data_manager.source import ConfiguredDataSource


def fetch_nt_titles(data_source: ConfiguredDataSource) -> pathlib.Path:
    """
    Download a zip file specified by DataSource.url, extract the contents and
    convert a Shapefile (.shp) to GeoJSON using geopandas.
    """
    # download zip file to a temporary location, it should be cleaned up afterwards
    zip_path, response = urllib.request.urlretrieve(
        url=data_source.url,
        filename=data_source.data_path / os.path.basename(data_source.url),
    )

    tmp_path = data_source.data_path / "zip_contents"
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(tmp_path)

    # read the extracted Shapefile with geopandas
    df = gpd.GeoDataFrame.from_file(tmp_path / "PETRO_TITLE_PROD_GRNT.shp")
    # remove entries with no granted date, these are unusable
    df = df[~np.isnat(df["DT_GRNT"])]

    # datetime64 objects aren't JSON serialisable, convert them to string
    for field_name in df.columns:
        if df.dtypes[field_name] == "datetime64[ms]":
            df[field_name] = [
                str(dt) if not np.isnat(dt) else None
                for dt in df[field_name].values
            ]

    # write the data as geojson
    with open(data_source.asset_path, "w") as asset_file:
        asset_file.write(df.to_json())

    # clean up the zip and extracted contents, leaving only the GeoJSON
    os.remove(zip_path)
    shutil.rmtree(tmp_path)

    return data_source.asset_path


# Locations of petroleum production titles in Australia's Northern Territories,
# via the Spatial Territory Resource Information Kit for Exploration (STRIKE),
# part of the NT Department of Mining and Energy.
# Source: http://strike.nt.gov.au/wss.html -> Downloads -> Petroleum Titles and Pipeline Titles
nt_titles_data_source = DataSource(
    name="NT-petroleum-titles",
    url="https://geoscience.nt.gov.au/contents/prod/Downloads/NT_PetroleumPipelineTitles_shp.zip",
    file_path='NT-petroleum-titles.geojson',
    fetch=fetch_nt_titles,
    parse=parse_geo,
)
