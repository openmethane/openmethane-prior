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

from openmethane_prior.lib import DataSource
from openmethane_prior.lib.data_manager.fetchers import fetch_google_sheet_csv
from openmethane_prior.lib.data_manager.source import ConfiguredDataSource


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
    fetch=fetch_google_sheet_csv("Oil and gas sites"),
    parse=parse_oil_gas_sites_csv,
)
