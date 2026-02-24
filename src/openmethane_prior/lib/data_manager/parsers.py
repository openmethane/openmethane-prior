#
# Copyright 2025 The Superpower Institute Ltd.
#
# This file is part of Open Methane.
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
import pandas as pd

from openmethane_prior.lib.data_manager.source import ConfiguredDataSource


def parse_csv(data_source: ConfiguredDataSource) -> pd.DataFrame:
    """Read and parse a ConfiguredDataSource CSV asset as a pandas DataFrame."""
    return pd.read_csv(data_source.asset_path)


def parse_geo(data_source: ConfiguredDataSource):
    """Read and parse a file containing a collection of geometry vector data
    into a geopandas GeoDataFrame. Asset file type can be anything supported by
    pyogrio, which includes GeoJSON, GeoPackage, Shapefiles, etc."""
    return gpd.read_file(data_source.asset_path)
