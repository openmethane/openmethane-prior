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
import pyproj

from openmethane_prior.lib.data_manager.source import ConfiguredDataSource


def parse_csv(data_source: ConfiguredDataSource) -> pd.DataFrame:
    """Read and parse a ConfiguredDataSource CSV asset as a pandas DataFrame."""
    return pd.read_csv(data_source.asset_path)


def parse_geo(data_source: ConfiguredDataSource, source_crs: pyproj.CRS = None):
    """Read and parse a file containing a collection of geometry vector data
    into a geopandas GeoDataFrame. Asset file type can be anything supported by
    pyogrio, which includes GeoJSON, GeoPackage, Shapefiles, etc."""
    geo_df = gpd.read_file(data_source.asset_path)

    if geo_df.crs is None:
        if source_crs is not None:
            geo_df = geo_df.set_crs(source_crs)
        else:
            raise ValueError("parse_geo could not determine CRS, must be called manually with source_crs parameter")

    # convert the geometries into the prior projection to ensure downstream
    # comparisons are done using the same coordinate system
    geo_df = geo_df.to_crs(data_source.prior_config.crs)

    return geo_df


def parse_xlsx(data_source: ConfiguredDataSource) -> pd.DataFrame:
    """Read and parse a ConfiguredDataSource XLSX asset as a pandas DataFrame."""
    return pd.read_excel(data_source.asset_path)


def parse_geo_xlsx(
    x_column: str,
    y_column: str,
    source_crs: pyproj.CRS | str,
):
    """Create a parser which will read an Excel-based ConfiguredDataSource,
    extracting coordinates from columns in x_column and y_column, and project
    coordinates from the source_crs to the PriorConfig domain CRS.

    This can be used to configure a DataSource like:
      DataSource(
        file_path="example.xlsx",
        parse=parse_geo_xlsx("x_col", "y_col", "EPSG:7844")
      )
    """
    def _parser(data_source: ConfiguredDataSource):
        df = parse_xlsx(data_source)

        df["geometry"] = gpd.points_from_xy(
            x=df[x_column],
            y=df[y_column],
            crs=source_crs,
        )
        geo_df = gpd.GeoDataFrame(df)

        # convert the geometries into the prior projection to ensure downstream
        # comparisons are done using the same coordinate system
        geo_df = geo_df.to_crs(data_source.prior_config.crs)

        return geo_df

    return _parser