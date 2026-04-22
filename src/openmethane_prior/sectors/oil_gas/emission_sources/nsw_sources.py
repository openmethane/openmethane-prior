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
from openmethane_prior.sectors.oil_gas.emission_sources.emission_source import normalise_emission_source_df

nsw_drillhole_purpose_map = {
    "Coal seam methane": "drillhole-csg",
    "Petroleum": "drillhole-petroleum",
}

def nsw_emission_sources(
    start_date: datetime.date,
    end_date: datetime.date,
    nsw_drillholes_da: DataAsset,
    nsw_titles_da: DataAsset,
) -> gpd.GeoDataFrame:
    """Create normalised emission source DataFrame by combining NSW petroleum
    drillhole dataset for locations, with land title dataset for production
    start/end dates."""
    nsw_drillholes_df: gpd.GeoDataFrame = nsw_drillholes_da.data
    nsw_titles_df: gpd.GeoDataFrame = nsw_titles_da.data

    # no specific date, so we'll guess from Jan 1st of the specified year
    nsw_drillholes_df["drilled_date"] = nsw_drillholes_df["year_drilled"].map(
        lambda year: datetime.datetime(int(year), 1, 1, 0, 0, 0)
    )

    # NSW drillhole dataset can contain multiple entries for a single exit
    # point, due to branches in a drill hole or extensions. Remove all but
    # the earliest record of the drilling at that location.
    nsw_drillholes_df = nsw_drillholes_df.sort_values(by="drilled_date")
    nsw_drillholes_df.drop_duplicates(subset="geometry", keep="first", inplace=True)

    # ignore the well title, we'll locate it spatially in a title instead
    del nsw_drillholes_df["title"]

    # map from PPL4 to PPL0004 to match formatting in drillholes dataset
    nsw_titles_df["title"] = nsw_titles_df["title"].map(
        lambda title: f"{title[:3]}{int(title[3:]):04d}"
    )

    # join drillholes with titles to use the title dates as start/end dates
    sources_df = gpd.sjoin(nsw_drillholes_df, nsw_titles_df, how="inner", predicate="within")

    # start date of emissions must be after hole is drilled and after the title
    # is granted, so choose the later of the two dates
    sources_df["start_date"] = [
        granted if granted > drilled else drilled
        for granted, drilled in sources_df[["grant_date", "drilled_date"]].values
    ]
    del sources_df["drilled_date"]
    del sources_df["grant_date"]

    # NSW drill holes are either coal seam methane or petroleum
    sources_df["site_type"] = sources_df["business_purpose"].map(
        lambda purpose: nsw_drillhole_purpose_map[purpose]
    )
    del sources_df["business_purpose"]

    # exclude any emission sources that would not have been emitting during
    # the period between start_date and end_date
    sources_df = rows_in_period(sources_df, start_date=start_date, end_date=end_date, end_field="expiry_date")

    # drop duplicates so there is only one entry for each location.
    sources_df = sources_df.drop_duplicates(["gsnsw_drill_id"])

    # normalise output to match emission sources format
    sources_df = sources_df.rename(columns={
        "gsnsw_drill_id": "data_source_id",
        "title": "group_id",
        "start_date": "activity_start",
        "expiry_date": "activity_end",
    })
    sources_df["data_source"] = nsw_drillholes_da.name

    return normalise_emission_source_df(sources_df)
