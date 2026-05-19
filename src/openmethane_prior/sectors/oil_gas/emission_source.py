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
import numpy as np
import geopandas as gpd
import pandas as pd
from typing import Any

"""
An "emission source" in the oil and gas sector is any location that forms part
of oil and gas extraction or production infrastructure where methane emission
might occur. Emission sources are gathered from a variety of datasets, but must
satisfy several required fields.
"""

emission_source_dtypes = {
    # The location of the site (typically a POINT or POLYGON). This column
    # is typically provided by GeoDataFrame.
    "geometry": "geometry",

    # A string which can be used to determine what type of site/facility is at
    # this location. Valid values are documented in emission_source_site_types.
    "site_type": str,

    # The earliest date emissions may have occurred at this site.
    "activity_start": np.datetime64,

    # The latest date emissions may have occurred at this site.
    "activity_end": np.datetime64,

    # (Optional) the "name" value of the data source where this site was
    # included.
    "data_source": str,

    # (Optional) a unique id for this site in the specified data source.
    "data_source_id": str,

    # (Optional) a string identifying a group of locations this site is part
    # of. A group could be a title/license area, a field, etc.
    "group_id": str,

    # (Optional) the state/region the emission source is in the jurisdiction
    # of. Can be useful for attributing inventory emissions, for example.
    "state": str,
}

emission_source_site_types = [
    "drillhole-unknown",
    "drillhole-csg",
    "drillhole-petroleum",
    "drillhole-gas",
]


def normalise_emission_source_df(
    df: gpd.GeoDataFrame,
    crs: Any, # anything supported by GeoDataFrame.to_crs
) -> gpd.GeoDataFrame:
    # select only columns which are present in emission_source_dtypes
    normalised_df = df[list(emission_source_dtypes.keys())].set_crs(df.crs)

    normalised_df = normalised_df.to_crs(crs)

    return normalised_df


def allocate_emissions_to_sources(
    sources_df: pd.DataFrame,
    sources_mask: "pd.Series[bool] | np.typing.NDArray[np.bool_]",
    emission_mass: float,
):
    """Distribute a single total emission across all emission sources in
    sources_df which match sources_mask."""
    # since we will use addition to allocate emission to each source, ensure
    # nans are replaced with zeros prior to addition
    is_nan = pd.isna(sources_df["emissions_quantity"])
    sources_df.loc[sources_mask & is_nan, "emissions_quantity"] = 0

    # divide the selected sources into drillholes and other facilities
    drillholes_mask = sources_mask \
                      & ~pd.isna(sources_df["site_type"]) \
                      & sources_df["site_type"].str.startswith("drillhole")
    facilities_mask = sources_mask & ~drillholes_mask

    # give each source an equal weighting when distributing the emissions
    sources_weight = sources_mask * 1.0

    # when there's a mix of drillholes and facilities, give the set of
    # facilities an equal weight to the set of drillholes. this naive
    # distribution assumes that every unit of extracted resource generates
    # emissions at the point of extraction and at least one facility.
    if drillholes_mask.sum() > 0 and facilities_mask.sum() > 0:
        sources_weight[facilities_mask] = drillholes_mask.sum() / facilities_mask.sum()

    # turn weight into a proportion of the total
    sources_weight /= sources_weight.sum()

    # naively allocate the emissions across each emission source equally
    sources_df["emissions_quantity"] += sources_weight * emission_mass
