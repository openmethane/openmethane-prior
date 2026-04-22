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
import pandas as pd

from openmethane_prior.lib import DataSource
from openmethane_prior.lib.data_manager.source import ConfiguredDataSource


def financial_year_start(financial_year: str) -> datetime.datetime:
    """Australian financial year starts on July 1st. For example, the 2023/2024
    financial year starts on 2023-07-01 00:00:00."""
    start_year, end_year = financial_year.split("/")
    return datetime.datetime(int(start_year), 7, 1, 0, 0)


def financial_year_end(financial_year: str | None) -> datetime.datetime | None:
    """Australian financial year ends on June 30th in the second year. For
    example, the 2023/2024 financial year ends on 2024-06-30 23:59:59."""
    if financial_year is None:
        return None

    start_year, end_year = financial_year.split("/")
    return datetime.datetime(int(end_year), 6, 30, 23, 59, 59)


def parse_npi_facilities_csv(data_source: ConfiguredDataSource) -> gpd.GeoDataFrame:
    """Read and parse the NPI facilities CSV asset, and convert to a
    GeoDataFrame using the latitude/longitude columns.

    Adds reporting_start_date and reporting_end_date columns derived from
    first_report_year and latest_report_year. Facilities whose
    latest_report_year matches the most recent reporting period in the dataset
    are assumed to still be operating (reporting_end_date is NaT)."""
    df = pd.read_csv(
        data_source.asset_path,
        converters={
            # ensure codes like "0700" are not turned into numeric 700
            "primary_anzsic_class_code": str,
        },
    )

    # add datetime columns to more easily work with reporting start/end dates
    df["reporting_start_date"] = df["first_report_year"].map(financial_year_start)

    # when latest_report_year matches the last reporting period, no
    # reporting_end_date is created, as we assume facility activity is ongoing
    last_report_period = df["latest_report_year"].max()
    latest_report_year = df["latest_report_year"].replace(last_report_period, None)
    df["reporting_end_date"] = latest_report_year.map(financial_year_end)

    # remove entries without lat/lon, these aren't useful to us
    df = df[(~np.isnan(df["longitude"])) & (~np.isnan(df["latitude"]))]

    gdf = gpd.GeoDataFrame(
        data=df.drop(columns=["longitude", "latitude"]),
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="EPSG:4326",
    )

    gdf = gdf.to_crs(data_source.prior_config.crs)

    return gdf


# National Pollutant Inventory published by the Commonwealth of Australia.
# This dataset includes lat/lon locations of facilities in many ANZSIC sectors
# which have reported industrial emissions.
# Although methane is not a reported substance under the NPI, the facility
# locations within an industrial sector is still very useful.
# Source: https://www.dcceew.gov.au/environment/protection/npi/data
npi_facilities_data_source = DataSource(
    name="NPI-facilities",
    url="https://data.gov.au/data/dataset/043f58e0-a188-4458-b61c-04e5b540aea4/resource/f83cdee9-ebcb-4f24-941b-34bb2f0996cf/download/facilities.csv",
    parse=parse_npi_facilities_csv,
)
