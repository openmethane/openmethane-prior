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
import pandas as pd
import pathlib
import urllib.parse

from openmethane_prior.lib import DataSource
from openmethane_prior.lib.data_manager.source import ConfiguredDataSource


def fetch_google_sheet_csv(
    sheet_id_or_url: str,
    sheet_name: str,
) -> pd.DataFrame:
    """Fetch a single sheet from a publicly viewable Google Sheet and return
    the contents as a pandas DataFrame."""
    if "://docs.google.com" in sheet_id_or_url:
        # if a url is provided, extract the sheet_id
        sheet_url = urllib.parse.urlparse(sheet_id_or_url)
        sheet_id = sheet_url.path.rpartition('/')[-1]
    else:
        sheet_id = sheet_id_or_url

    # remove strings from the sheet name so it is url-safe
    sheet_name = sheet_name.replace(" ", "")

    # Google Sheets provides a CSV endpoint for downloading
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&amp;sheet={sheet_name}"
    df = pd.read_csv(url)

    # remove empty columns with no name or data
    for column_name in df.columns:
        if "Unnamed: " in column_name and df[column_name].isnull().all():
            del df[column_name]

    return df


def fetch_oil_gas_sites_csv(data_source: ConfiguredDataSource) -> pathlib.Path:
    """Fetch the oil and gas sites from Google Sheets and save as a CSV."""
    df = fetch_google_sheet_csv(data_source.url, "Oil and gas sites")
    df.to_csv(data_source.asset_path)
    return data_source.asset_path


def parse_oil_gas_sites_csv(data_source: ConfiguredDataSource) -> gpd.GeoDataFrame:
    """Read and parse the oil-gas-processing CSV asset, and convert to a
    GeoDataFrame using the latitude/longitude columns."""
    df = pd.read_csv(
        data_source.asset_path,
        converters={
            "Operation start": np.datetime64,
            "Operation end": np.datetime64,
        },
    )

    # remove entries without lat/lon, these aren't useful to us
    df = df[(~np.isnan(df["Longitude"])) & (~np.isnan(df["Latitude"]))]

    gdf = gpd.GeoDataFrame(
        data=df,
        geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]),
        crs="EPSG:4326",
    )
    del gdf["Longitude"]
    del gdf["Latitude"]

    gdf = gdf.to_crs(data_source.prior_config.crs)

    return gdf


# Processing facilities in the oil and gas industry in Australia. This dataset,
# created by The Superpower Institute, identifies locations of oil and gas
# sites linked to Safeguard Mechanism facilities.
# Source: https://docs.google.com/spreadsheets/d/1vET6DVXo3K9MeMYJj9sksSTmQjV3v9JmIPSlR6HS4NA
oil_gas_sites_data_source = DataSource(
    name="oil-gas-sites",
    file_path="oil-gas-sites.csv",
    url="https://docs.google.com/spreadsheets/d/1vET6DVXo3K9MeMYJj9sksSTmQjV3v9JmIPSlR6HS4NA",
    fetch=fetch_oil_gas_sites_csv,
    parse=parse_oil_gas_sites_csv,
)
