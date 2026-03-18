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
import pyproj

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
}

emission_source_site_types = [
    "drillhole-unknown",
    "drillhole-csg",
    "drillhole-petroleum",
    "drillhole-gas",
]


def normalise_emission_source_df(
    df: gpd.GeoDataFrame,
    crs: pyproj.CRS = pyproj.CRS.from_epsg(4326),
) -> gpd.GeoDataFrame:
    # select only columns which are present in emission_source_dtypes
    normalised_df = df[list(emission_source_dtypes.keys())]

    normalised_df = normalised_df.to_crs(crs)

    return normalised_df