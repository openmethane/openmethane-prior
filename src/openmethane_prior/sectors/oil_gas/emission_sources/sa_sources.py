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

from openmethane_prior.lib.data_manager.asset import DataAsset
from openmethane_prior.lib.utils import rows_in_period


def start_of_month(date: pd.Timestamp) -> np.datetime64:
    return np.datetime64(pd.Timestamp(year=date.year, month=date.month, day=1))

def sa_emission_sources(
    start_date: datetime.date,
    end_date: datetime.date,
    sa_wells_da: DataAsset,
    sa_production_da: DataAsset,
) -> gpd.GeoDataFrame:
    """Create normalised emission source DataFrame by combining SA petroleum
    wells dataset for locations, with petroleum title dataset for production
    start/end dates."""
    sa_wells_df: gpd.GeoDataFrame = sa_wells_da.data
    sa_production_df: gpd.GeoDataFrame = sa_production_da.data

    # filter out non-production wells
    sa_emitting_types = [
        "Oil Shows", "Oil",
        "Gas Shows", "Gas",
        "Oil and Gas", "Oil and Gas Shows", "Oil with Gas Shows",
        "Gas with Oil Shows", "CO2 with Oil Shows",
    ]
    wells_df = sa_wells_df[sa_wells_df["Type"].isin(sa_emitting_types)]

    # "Month End" is read from a date on the last day of the month, construct
    # a start/end date reflecting the full period ending on midnight of "Month End",
    # then filter to only rows that intersect with the prior period.
    sa_production_df["activity_start"] = sa_production_df["Month End"].map(start_of_month)
    sa_production_df["activity_end"] = sa_production_df["Month End"] + np.timedelta64(1, "D")
    production_df = rows_in_period(
        sa_production_df,
        start_date=start_date,
        end_date=end_date,
        start_field="activity_start",
        end_field="activity_end",
    )

    # Production values are split by Co-Formation, but we just want the sum
    # of production for each well
    production_df = production_df.groupby("WellID", as_index=False)
    production_df = production_df.agg({
        "Oil (m3)": "sum",
        "Gas (m3E6)": "sum",
        "Type": "first",
        "Field": "first",
        "activity_start": "first",
        "activity_end": "first",
        "Month Days": "first",
    })
    production_df = production_df.rename({"WellID": "Well ID"})  # join column

    # join well details with production figures
    sources_df = wells_df.join(production_df, on="Well ID", how="inner", rsuffix=" Production")

    # remove wells which didn't produce during the period of interest
    sources_df = sources_df[(sources_df["Oil (m3)"] > 0) | (sources_df["Gas (m3E6)"] > 0)]

    sources_df["License"] = [
        None if current_ppl is None else f"PPL {current_ppl:0.0f}"
        for current_ppl in sources_df["Current PPL"].values
    ]

    # normalise output to match emission sources format
    sources_df = sources_df.rename(columns={
        "Well ID": "data_source_id",
        "License": "group_id",
    })
    sources_df["data_source"] = sa_wells_da.name
    sources_df["site_type"] = [
        "drillhole-oil" if production_type == "Oil" else "drillhole-gas"
        for production_type in sources_df["Type Production"].values
    ]

    return sources_df
