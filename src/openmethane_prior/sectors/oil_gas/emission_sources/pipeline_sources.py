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

from openmethane_prior.data_sources.au_shapes import map_state_name_to_short_name
from openmethane_prior.lib import DataAsset

pipeline_type_map = {
    "Gas pipeline": "pipeline-gas",
    "Oil pipeline": "pipeline-oil",
}


def pipeline_emission_sources(
    start_date: datetime.date,
    end_date: datetime.date,
    gas_pipelines_da: DataAsset,
) -> gpd.GeoDataFrame:
    """Create normalised emission source DataFrame of gas pipelines."""
    sources_df: gpd.GeoDataFrame = gas_pipelines_da.data

    # emission sources must use state abbreviations (i.e. "NSW")
    sources_df["state"] = sources_df["state"].map(map_state_name_to_short_name)

    # Pipeline dataset may include gas and oil pipelines, as well as proposed
    # pipelines. Filter out proposed pipelines and map to a site_type value.
    sources_df["site_type"] = sources_df["feature_type"].map(
        lambda pipe_type: pipeline_type_map[pipe_type]
            if pipe_type in pipeline_type_map
            else None
    )
    sources_df = sources_df[~pd.isna(sources_df["site_type"])]

    sources_df = sources_df[sources_df["operational_status"] == "Fully capable of operation."]

    # Unfortunately, the pipeline dataset doesn't include dates when a pipeline
    # began or ceased operation

    # normalise output to match emission sources format
    sources_df = sources_df.rename(columns={
        "objectid": "data_source_id",
        "name": "group_id",
        "length": "weight", # use pipeline length as a weighting
        # "start_date": "activity_start",
        # "expiry_date": "activity_end",
    })
    sources_df["activity_start"] = pd.NaT
    sources_df["activity_end"] = pd.NaT
    sources_df["data_source"] = gas_pipelines_da.name

    return sources_df
