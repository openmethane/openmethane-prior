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
import datetime
import geopandas as gpd
import numpy as np
import os
import pathlib
import shutil
import tempfile
import urllib
import zipfile

from openmethane_prior.lib import DataSource
from openmethane_prior.lib.data_manager.parsers import parse_geo
from openmethane_prior.lib.data_manager.source import ConfiguredDataSource

def fetch_zipped_shp_to_gdf(
    url: str,
    shp_file: str,
) -> gpd.GeoDataFrame:
    """Fetch a zip file specified by DataSource.url, extract the contents and
    read in a Shapefile (.shp) from the archive as a GeoDataFrame."""

    # use a temporary path to store and extract the zip contents, which will
    # be cleaned up automatically afterwards
    with tempfile.TemporaryDirectory(prefix="openmethane-prior") as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)

        # download and extract the zip file to a known location
        zip_path, response = urllib.request.urlretrieve(
            url=url,
            filename=tmp_path / os.path.basename(url),
        )
        # entire zip must be extracted, as the .shp file depends on sibling files
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmp_path)

        # read the extracted Shapefile with geopandas
        return gpd.read_file(tmp_path / shp_file)


def fetch_nt_titles(data_source: ConfiguredDataSource) -> pathlib.Path:
    """Fetch a zipped Shapefile (.shp) and convert to GeoJSON using geopandas."""
    # fetch the zipfile in data_source.url and read the included Shapefile
    df = fetch_zipped_shp_to_gdf(data_source.url, "PETRO_TITLE_PROD_GRNT.shp")

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


def fetch_nt_wells(data_source: ConfiguredDataSource) -> pathlib.Path:
    """Fetch a zipped Shapefile (.shp) and convert to GeoJSON using geopandas."""
    # fetch the zipfile in data_source.url and read the included Shapefile
    df = fetch_zipped_shp_to_gdf(data_source.url, "PETROLEUM_WELLS.shp")

    # convert datetime fields with strings like "19891229000000" into RFC3339
    for field_name in df.columns:
        if field_name.startswith("DT_"):
            df[field_name] = [
                str(datetime.datetime.strptime(dt_str, "%Y%m%d%H%M%S")) if dt_str is not None else None
                for dt_str in df[field_name].values
            ]

    # write the data as geojson
    with open(data_source.asset_path, "w") as asset_file:
        asset_file.write(df.to_json())

    return data_source.asset_path


# Locations of petroleum wells in Australia's Northern Territories, via the
# Spatial Territory Resource Information Kit for Exploration (STRIKE), part of
# the NT Department of Mining and Energy.
# Source: http://strike.nt.gov.au/wss.html -> Downloads -> Drilling -> Petroleum Wells
# Metadata: https://www.ntlis.nt.gov.au/metadata/export_data?type=html&metadata_id=2DBCB771210D06B6E040CD9B0F274EFE
nt_wells_data_source = DataSource(
    name="NT-petroleum-wells",
    url="https://geoscience.nt.gov.au/contents/prod/Downloads/Drilling/PETROLEUM_WELLS_shp.zip",
    file_path='NT-petroleum-wells.geojson',
    fetch=fetch_nt_wells,
    parse=parse_geo,
)
