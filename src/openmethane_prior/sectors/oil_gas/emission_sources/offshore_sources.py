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


def offshore_emission_sources(
    start_date: datetime.date,
    end_date: datetime.date,
    offshore_wells_da: DataAsset,
    offshore_titles_da: DataAsset,
) -> gpd.GeoDataFrame:
    """Create normalised emission source DataFrame by combining WA petroleum
    wells dataset for locations, with land title dataset for production
    start/end dates."""
    offshore_wells_df: gpd.GeoDataFrame = offshore_wells_da.data
    offshore_titles_df: gpd.GeoDataFrame = offshore_titles_da.data

    # filter out wells that aren't actively used for production
    wells_df = offshore_wells_df[offshore_wells_df["Purpose"] == "Development"]

    # emissions are expected where production is ongoing, unlike exploration or retention
    titles_df = offshore_titles_df[offshore_titles_df["TitleType"] == "Production Licence"]
    titles_df = titles_df.rename(columns={"state": "title_state"})

    # NOPTA wells dataset appears to re-use lat/lon coords for multiple wells
    # within the same field. Since these contain unique values for WellName and
    # RigReleaseDate, we treat these as unique wells and don't de-duplicate

    # join drillholes with titles to use the title dates as start/end dates
    sources_df = gpd.sjoin(wells_df, titles_df, how="inner", predicate="within")

    # start date of emissions must be after hole is drilled and after the title
    # is granted, so choose the latter of the two dates
    sources_df["start_date"] = [
        issued if not np.isnat(issued) and (np.isnat(drilled) or issued > drilled) else drilled
        for issued, drilled in sources_df[["GrantDate", "RigReleaseDate"]].values
    ]
    del sources_df["GrantDate"]
    del sources_df["RigReleaseDate"]

    # exclude any emission sources that would not have been emitting during
    # the period between start_date and end_date
    sources_df = rows_in_period(sources_df, start_date=start_date, end_date=end_date, end_field="ExpiryDate")

    # after the join with titles, there may be multiple rows for each well.
    # drop duplicates so there is only one entry for each location.
    sources_df = sources_df.drop_duplicates(["WellName"])

    # normalise output to match emission sources format
    sources_df = sources_df.rename(columns={
        "WellName": "data_source_id",
        "Title": "group_id",
        "start_date": "activity_start",
        "ExpiryDate": "activity_end",
    })
    sources_df["data_source"] = offshore_wells_da.name
    # not enough detail in the data source to determine the type of resource
    # being extracted by the well
    sources_df["site_type"] = "drillhole-unknown"

    return sources_df
