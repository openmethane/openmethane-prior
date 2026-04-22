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
from openmethane_prior.lib.data_manager.source import ConfiguredDataSource


def parse_au_npi_csv(data_source: ConfiguredDataSource) -> gpd.GeoDataFrame:
    """Read and parse the oil-gas-processing CSV asset, and convert to a
    GeoDataFrame using the latitude/longitude columns."""
    df = pd.read_csv(
        data_source.asset_path,
        converters={
            # ensure codes like "0700" are not turned into numeric 700
            "primary_anzsic_class_code": str,
        },
    )

    # remove entries without lat/lon, these aren't useful to us
    df = df[(~np.isnan(df["longitude"])) & (~np.isnan(df["latitude"]))]

    gdf = gpd.GeoDataFrame(
        data=df,
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="EPSG:4326",
    )
    del gdf["longitude"]
    del gdf["latitude"]

    gdf = gdf.to_crs(data_source.prior_config.crs)

    return gdf


# Processing facilities in the oil and gas industry in Australia. This dataset
# was manually created from research conducted by The Superpower Institute to
# identify locations of processing sites linked to Safeguard Mechanism facilities.
au_npi_data_source = DataSource(
    name="AU-NPI",
    url="https://data.gov.au/data/dataset/043f58e0-a188-4458-b61c-04e5b540aea4/resource/f83cdee9-ebcb-4f24-941b-34bb2f0996cf/download/facilities.csv",
    parse=parse_au_npi_csv,
)
