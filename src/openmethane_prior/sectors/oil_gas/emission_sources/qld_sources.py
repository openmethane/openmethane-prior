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
from openmethane_prior.sectors.oil_gas.emission_sources.emission_source import normalise_emission_source_df

bore_type_map = {
    "COAL SEAM GAS": "drillhole-csg",
    "PETROLEUM": "drillhole-petroleum",
    "UNCONVENTIONAL PETROLEUM": "drillhole-unknown",
}

def qld_emission_sources(
    start_date: datetime.date,
    end_date: datetime.date,
    qld_boreholes_da: DataAsset,
    qld_leases_da: DataAsset,
) -> gpd.GeoDataFrame:
    """Create normalised emission source DataFrame by combining WA petroleum
    wells dataset for locations, with land title dataset for production
    start/end dates."""
    qld_boreholes_df: gpd.GeoDataFrame = qld_boreholes_da.data
    qld_leases_df: gpd.GeoDataFrame = qld_leases_da.data

    # filter non-production and storage wells
    emitting_bore_types = ["COAL SEAM GAS", "PETROLEUM", "UNCONVENTIONAL PETROLEUM", "GREENHOUSE GAS STORAGE"]
    qld_boreholes_df = qld_boreholes_df[qld_boreholes_df["bore_type"].isin(emitting_bore_types)]
    emitting_bore_subtypes = ["DEVELOPMENT WELL", "COAL SEAM GAS INJECTION WELL", "PETROLEUM INJECTION WELL"]
    qld_boreholes_df = qld_boreholes_df[qld_boreholes_df["bore_subtype"].isin(emitting_bore_subtypes)]

    # filter bores without hydrocarbons
    non_emitting_bore_result = ['NO HYDROCARBONS', 'UNKNOWN', 'COAL', 'WATER', 'NO COAL INTERSECTED']
    qld_boreholes_df = qld_boreholes_df[~qld_boreholes_df["result"].isin(non_emitting_bore_result)]
    non_emitting_bore_status = ['WATER BORE', 'UNKNOWN']
    qld_boreholes_df = qld_boreholes_df[~qld_boreholes_df["status"].isin(non_emitting_bore_status)]

    # bore datasets may have duplicate rows for a single location due to
    # further drilling at a site to deepen/extend an existing hole
    qld_boreholes_df = qld_boreholes_df.sort_values(by="rig_release_date")
    qld_boreholes_df.drop_duplicates(subset="geometry", keep="first", inplace=True)

    # join boreholes with titles to use the title dates as start/end dates
    sources_df = gpd.sjoin(qld_boreholes_df, qld_leases_df, how="inner", predicate="within")

    # start date of emissions must be after hole is drilled and after the title
    # is granted, so choose the latter of the two dates
    sources_df["start_date"] = [
        issued if not np.isnat(issued) and (np.isnat(drilled) or issued > drilled) else drilled
        for issued, drilled in sources_df[["approvedate", "rig_release_date"]].values
    ]
    del sources_df["approvedate"]
    del sources_df["rig_release_date"]

    # exclude any emission sources that would not have been emitting during
    # the period between start_date and end_date
    sources_df = rows_in_period(sources_df, start_date=start_date, end_date=end_date, end_field="expirydate")

    # after the join with titles, there may be multiple rows for each well.
    # drop duplicates so there is only one entry for each location.
    sources_df = sources_df.drop_duplicates(["borehole_pid"])

    # normalise output to match emission sources format
    sources_df = sources_df.rename(columns={
        "borehole_pid": "data_source_id",
        "displayname": "group_id",
        "start_date": "activity_start",
        "expirydate": "activity_end",
    })
    sources_df["data_source"] = qld_boreholes_da.name
    sources_df["site_type"] = sources_df["bore_type"].map(
        lambda bore_type: bore_type_map[bore_type] if bore_type in bore_type_map else "drillhole-unknown"
    )

    return normalise_emission_source_df(sources_df)
