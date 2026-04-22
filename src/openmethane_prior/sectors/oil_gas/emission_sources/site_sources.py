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

from openmethane_prior.data_sources.npi import filter_npi_facilities
from openmethane_prior.data_sources.safeguard.facility import parse_anzsic_code
from openmethane_prior.lib import DataAsset
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

    # extract the ANZSIC code from the Safeguard Mechanism format
    sites_df["anzsic_code"] = sites_df["ANZSIC"].map(parse_anzsic_code)

    # exclude any emission sources that would not have been in operation
    # the period between start_date and end_date
    sites_df = rows_in_period(
        sites_df,
        start_date=start_date, end_date=end_date,
        start_field="Operation start", end_field="Operation end",
    )

    # exclude sources that aren't in ANZSIC sector 070
    sites_df = sites_df[sites_df["anzsic_code"] == "070"]

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
    npi_df: gpd.GeoDataFrame = filter_npi_facilities(
        facilities_df=npi_da.data,
        period_start=start_date,
        period_end=end_date,
        anzsic_codes=["070"],
    )

    # locate NPI facilities within 250m of sites already accounted for in the
    # oil and gas sites dataset, so they don't get counted twice
    npi_duplicate_df = gpd.sjoin_nearest(
        npi_df,
        sites_df,
        how="inner",
        max_distance=250, # 250m, assumes the domain CRS is in meters
        distance_col="distance",
    )

    # remove npi facilities within 250m of a site from our other dataset
    npi_df = npi_df[~npi_df.index.isin(npi_duplicate_df.index)]

    # normalise output to match emission sources format
    npi_df = npi_df.rename(columns={
        "facility_id": "data_source_id",
        "abn": "group_id",
        "start_date": "activity_start",
        "expiry_date": "activity_end",
        "primary_anzsic_class_code": "anzsic_code",
    })
    npi_df["data_source"] = npi_da.name

    sources_df: gpd.GeoDataFrame = pd.concat([sites_df, npi_df])

    return sources_df
