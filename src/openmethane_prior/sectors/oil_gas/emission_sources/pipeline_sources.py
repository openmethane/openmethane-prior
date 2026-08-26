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

from openmethane_prior.lib import DataAsset, logger

logger = logger.get_logger(__name__)

pipeline_type_map = {
    "Gas Pipeline": "pipeline-gas",
    "Oil Pipeline": "pipeline-oil",
}

# Segments shorter than this fraction of a pipeline's total length are treated
# as an artifact of imprecision in the state border geometry rather than a real
# crossing, and are discarded.
MIN_SEGMENT_FRACTION = 0.001

# Tolerance used to simplify state shapes before finding the state nearest to
# an offshore pipeline. Matching against the full-resolution coastline is very
# slow, and the nearest state is never a close call.
NEAREST_STATE_SIMPLIFY_M = 1000


def split_pipelines_by_state(
    pipelines_df: gpd.GeoDataFrame,
    au_states_df: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Annotate each pipeline with the state it lies in.

    Pipelines which cross a state border are split into one segment per state.

    Until 2026 the source dataset provided a "state" field, and represented a
    pipeline crossing a state border as a separate entity per state. Both of
    those went away when the dataset changed format, so we reconstruct them by
    intersecting pipeline shapes with state shapes.

    "length_km" is the weight used to allocate a share of emissions to each
    pipeline, so it is divided between the segments of a split pipeline in
    proportion to their geometric length. This preserves the total length of
    the original pipeline, and keeps the authoritative length from the source
    dataset rather than substituting our own measurement of it.

    Offshore pipelines fall outside every state shape, and are attributed to
    the nearest state. These are not split and keep their full length.

    :param pipelines_df: Pipelines, with "objectid" and "length_km" columns
    :param au_states_df: GeoDataFrame with the shape of each state
    :return: Pipelines with a "state" column, split at state borders
    """
    states_df = au_states_df[au_states_df.geometry.notna()][["short_name", "geometry"]]
    states_df = states_df.rename(columns={"short_name": "state"})

    # Intersecting every pipeline with the state shapes is slow, and would clip
    # the offshore portion off any pipeline that runs out to sea. Only the
    # pipelines which actually touch more than one state need to be split, so
    # use a cheaper spatial join to find them first.
    state_matches = gpd.sjoin(
        pipelines_df[["objectid", "geometry"]],
        states_df,
        how="left",
        predicate="intersects",
    )
    states_per_pipeline = state_matches.groupby("objectid")["state"].nunique()

    single_state_ids = states_per_pipeline[states_per_pipeline == 1].index
    multi_state_ids = states_per_pipeline[states_per_pipeline > 1].index
    # pipelines which intersect no state at all are offshore
    offshore_ids = states_per_pipeline[states_per_pipeline == 0].index

    # pipelines within a single state keep their geometry and length as-is
    single_df = pipelines_df[pipelines_df["objectid"].isin(single_state_ids)].merge(
        state_matches[state_matches["objectid"].isin(single_state_ids)][["objectid", "state"]],
        on="objectid",
    )

    # split the pipelines which cross a border into one segment per state
    split_df = _split_at_state_borders(
        pipelines_df[pipelines_df["objectid"].isin(multi_state_ids)],
        states_df,
    )

    # attribute offshore pipelines to whichever state is closest
    offshore_df = pipelines_df[pipelines_df["objectid"].isin(offshore_ids)]
    if len(offshore_df) > 0:
        coarse_states_df = states_df.copy()
        coarse_states_df["geometry"] = coarse_states_df.geometry.simplify(
            NEAREST_STATE_SIMPLIFY_M,
        )
        offshore_df = gpd.sjoin_nearest(offshore_df, coarse_states_df, how="left").drop(
            columns="index_right",
        )

    logger.debug(
        f"{len(single_df)} pipelines in one state, "
        f"{len(multi_state_ids)} split into {len(split_df)} segments, "
        f"{len(offshore_df)} offshore attributed to nearest state"
    )

    return pd.concat([single_df, split_df, offshore_df], ignore_index=True)


def _split_at_state_borders(
    crossing_df: gpd.GeoDataFrame,
    states_df: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """Split pipelines which cross a state border, at the border.

    "length_km" is divided between the resulting segments in proportion to
    their length.
    """
    if len(crossing_df) == 0:
        return crossing_df.assign(state=pd.Series(dtype=str))

    segments_df = gpd.overlay(crossing_df, states_df, how="intersection", keep_geom_type=True)

    # measure each segment so length_km can be divided between them. the
    # measurement is only used as a ratio of segments of the same pipeline, so
    # any distortion in the projection cancels out.
    segment_length = segments_df.geometry.length
    pipeline_length = segment_length.groupby(segments_df["objectid"]).transform("sum")
    segment_fraction = segment_length / pipeline_length

    # discard slivers produced where a pipeline runs alongside a border rather
    # than across it, then re-derive the fractions from the segments we keep so
    # they still account for the whole pipeline
    segments_df = segments_df[segment_fraction >= MIN_SEGMENT_FRACTION].copy()
    segment_length = segments_df.geometry.length
    pipeline_length = segment_length.groupby(segments_df["objectid"]).transform("sum")

    segments_df["length_km"] *= segment_length / pipeline_length

    # objectid identifies the pipeline, so it is no longer unique once a
    # pipeline has been split. qualify it with the state to keep it unique.
    segments_df["objectid"] = (
        segments_df["objectid"].astype(str) + "-" + segments_df["state"]
    )

    return segments_df


def pipeline_emission_sources(
    start_date: datetime.date,
    end_date: datetime.date,
    gas_pipelines_da: DataAsset,
    au_states_da: DataAsset,
) -> gpd.GeoDataFrame:
    """Create normalised emission source DataFrame of gas pipelines."""
    sources_df: gpd.GeoDataFrame = gas_pipelines_da.data

    # Pipeline dataset may include gas and oil pipelines, as well as proposed
    # pipelines. Filter out proposed pipelines and map to a site_type value.
    sources_df["site_type"] = sources_df["feature_type"].map(
        lambda pipe_type: pipeline_type_map[pipe_type]
            if pipe_type in pipeline_type_map
            else None
    )
    sources_df = sources_df[~pd.isna(sources_df["site_type"])]

    sources_df = sources_df[sources_df["status"] == "Fully capable of operation"]

    # the dataset no longer provides a state, so derive it from the geometry
    sources_df = split_pipelines_by_state(sources_df, au_states_da.data)

    # Unfortunately, the pipeline dataset doesn't include dates when a pipeline
    # began or ceased operation

    # normalise output to match emission sources format
    sources_df = sources_df.rename(columns={
        "objectid": "data_source_id",
        "feature_name": "group_id",
        "length_km": "weight", # use pipeline length as a weighting
        # "start_date": "activity_start",
        # "expiry_date": "activity_end",
    })
    sources_df["activity_start"] = pd.NaT
    sources_df["activity_end"] = pd.NaT
    sources_df["data_source"] = gas_pipelines_da.name

    return sources_df
