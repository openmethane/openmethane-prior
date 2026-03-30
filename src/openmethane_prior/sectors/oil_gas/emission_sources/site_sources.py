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


def oil_gas_site_emission_sources(
    start_date: datetime.date,
    end_date: datetime.date,
    oil_gas_sites_da: DataAsset,
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
    sources_df = sites_df.rename(columns={
        "Site": "data_source_id",
        "Facility name": "group_id",
        "Operation start": "activity_start",
        "Operation end": "activity_end",
    })
    sources_df["data_source"] = oil_gas_sites_da.name

    return sources_df
