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

from openmethane_prior.lib.data_manager.asset import DataAsset
from openmethane_prior.lib.utils import rows_in_period


def nt_emission_sources(
    start_date: datetime.date,
    end_date: datetime.date,
    nt_wells_da: DataAsset,
    nt_titles_da: DataAsset,
) -> gpd.GeoDataFrame:
    """Create normalised emission source DataFrame by combining NT petroleum
    wells dataset for locations, with petroleum title dataset for production
    start/end dates."""
    nt_wells_df: gpd.GeoDataFrame = nt_wells_da.data
    nt_titles_df: gpd.GeoDataFrame = nt_titles_da.data

    # filter out non-production wells
    emitting_well_purposes = ["Development", "Production"]
    nt_wells_df = nt_wells_df[nt_wells_df["PURPOSE"].isin(emitting_well_purposes)]

    # well datasets may have duplicate rows for a single location due to
    # further drilling at a site to deepen/extend an existing hole
    nt_wells_df = nt_wells_df.sort_values(by="DT_RELEASE")
    nt_wells_df.drop_duplicates(subset="geometry", keep="first", inplace=True)

    # dataset includes multiple rows for each title when the controlling entity
    # ("PTY_NAME") has changed, we only want a single row per title
    nt_titles_df.drop_duplicates(subset="TITLEID", keep="last", inplace=True)

    # join wells with titles to use the title dates as start/end dates
    sources_df = gpd.sjoin(nt_wells_df, nt_titles_df, how="inner", predicate="within")

    # start date of emissions must be after hole is drilled (DT_RELEASE, drill
    # release date) and after the title is granted (DT_GRNT), so use the latter
    # of the two dates
    sources_df["start_date"] = [
        issued if not np.isnat(issued) and (np.isnat(drilled) or issued > drilled) else drilled
        for issued, drilled in sources_df[["DT_GRNT", "DT_RELEASE"]].values
    ]
    del sources_df["DT_GRNT"]
    del sources_df["DT_RELEASE"]

    # exclude any emission sources that would not have been emitting during
    # the period between start_date and end_date
    sources_df = rows_in_period(sources_df, start_date=start_date, end_date=end_date, end_field="DT_EXPIRY")

    # after the join with titles, there may be multiple rows for each well.
    # drop duplicates so there is only one entry for each location.
    sources_df = sources_df.drop_duplicates(["WELLNAME"])

    # normalise output to match emission sources format
    sources_df = sources_df.rename(columns={
        "WELLNAME": "data_source_id",
        "TITLEID": "group_id",
        "start_date": "activity_start",
        "DT_EXPIRY": "activity_end",
    })
    sources_df["data_source"] = nt_wells_da.name
    sources_df["site_type"] = "drillhole-unknown"

    return sources_df
