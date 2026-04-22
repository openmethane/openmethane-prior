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
import pandas as pd

from openmethane_prior.lib.data_manager.asset import DataAsset
from openmethane_prior.lib.utils import rows_in_period


site_type_map = {
    "Compressor station": "gas-compressor",
    "Floating LNG": "flng",
    "FPSO": "fpso", # https://en.wikipedia.org/wiki/Floating_production_storage_and_offloading
    "Gas processing": "gas-processing",
    "Gas production": "gas-production",
    "LNG terminal": "lng-terminal",
    "Oil separation": "oil-separation",
    "Oil waste disposal": "oil-waste",
    "Oil processing": "oil-processing",
    "WHP": "whp",
    "LNG power plant": "lng-power-plant",
}
def map_site_type_to_source_type(site_type: str) -> str | None:
    return site_type_map[site_type] if site_type in site_type_map else None


def _npi_financial_year_start(financial_year: str) -> datetime.datetime:
    """Australian financial year starts on July 1st. For example, the 2023/2024
    financial year starts on 2023-07-01 00:00:00."""
    start_year, end_year = financial_year.split("/")
    return datetime.datetime(int(start_year), 7, 1, 0, 0)


def _npi_financial_year_end(financial_year: str) -> datetime.datetime:
    """Australian financial year ends on June 30th in the second year. For
    example, the 2023/2024 financial year ends on 2024-06-30 23:59:59."""
    start_year, end_year = financial_year.split("/")
    return datetime.datetime(int(end_year), 7, 1, 0, 0)


def oil_gas_site_emission_sources(
    start_date: datetime.date,
    end_date: datetime.date,
    oil_gas_sites_da: DataAsset,
    npi_da: DataAsset,
) -> gpd.GeoDataFrame:
    """Create normalised emission source GeoDataFrame for known oil and gas
    sector sites and facilities, not including oil and gas wells."""
    sites_df: gpd.GeoDataFrame = oil_gas_sites_da.data

    # Sites are roughly classified in the input dataset, map those to emission
    # source types
    sites_df["site_type"] = sites_df["Type"].map(map_site_type_to_source_type)
    del sites_df["Type"]

    # Exclude any sites that aren't ANZSIC 070
    sites_df = sites_df[sites_df["ANZSIC"] == "Oil and gas extraction (070)"]

    # exclude any emission sources that would not have been in operation
    # the period between start_date and end_date
    sites_df = rows_in_period(
        sites_df,
        start_date=start_date, end_date=end_date,
        start_field="Operation start", end_field="Operation end",
    )

    # normalise output to match emission sources format
    sites_df = sites_df.rename(columns={
        "Site": "data_source_id",
        "Facility name": "group_id",
        "Operation start": "activity_start",
        "Operation end": "activity_end",
    })
    sites_df["data_source"] = oil_gas_sites_da.name

    # the national pollutant inventory doesn't track methane emissions, but it
    # does include the locations of industrial facilities in different ANSIC
    # sectors.
    npi_df: gpd.GeoDataFrame = npi_da.data

    # Remove facilities not in the "070" (oil and gas) ANZSIC sector
    npi_df = npi_df[npi_df["primary_anzsic_class_code"].str.startswith("070")]

    # NPI is based on a reporting mechanism. Lacking more detailed information,
    # this assumes that each facility operates continuously from the start
    # of the first reporting period where a facility report was lodged, until
    # the end of the reporting period when the last report was filed.
    npi_df["start_date"] = npi_df["first_report_year"].map(_npi_financial_year_start)
    npi_df["end_date"] = npi_df["latest_report_year"].map(_npi_financial_year_end)
    npi_df = rows_in_period(df=npi_df, start_date=start_date, end_date=end_date)

    # locate NPI facilities within 250m of sites already accounted for in the
    # oil and gas sites dataset, so they don't get counted twice
    npi_duplicate_df = gpd.sjoin_nearest(
        npi_df,
        sites_df,
        how="inner",
        max_distance=250, # 250m, assumes the domain CRS is in meters
        distance_col="distance",
    )

    npi_df = npi_df[~npi_df.index.isin(npi_duplicate_df.index)]

    # normalise output to match emission sources format
    npi_df = npi_df.rename(columns={
        "facility_id": "data_source_id",
        "abn": "group_id",
        "start_date": "activity_start",
        "expiry_date": "activity_end",
    })
    npi_df["data_source"] = npi_da.name

    sources_df: gpd.GeoDataFrame = pd.concat([sites_df, npi_df])

    return sources_df
