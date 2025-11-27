#
# Copyright 2025 The Superpower Institute Ltd.
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
import pandas as pd


def filter_locations(
    locations_df: pd.DataFrame,
    facility_id: str = None,
    data_source_name: str = None,
    data_source_id: str = None,
):
    """Filter a locations DataFrame by different column values"""
    if facility_id is not None:
        locations_df = locations_df[locations_df.safeguard_facility_name == facility_id]

    if data_source_name is not None:
        locations_df = locations_df[locations_df.data_source_name == data_source_name]

    if data_source_id is not None:
        locations_df = locations_df[locations_df.data_source_id == data_source_id]

    return locations_df


def get_safeguard_facility_locations(
    safeguard_facilities_df: pd.DataFrame,
    locations_df: pd.DataFrame,
    data_source_name: str,
):
    """Return facility locations referenced in a specific data source, and a
    filtered list of the Safeguard Mechanism facilities they relate to."""
    source_locations = filter_locations(
        locations_df=locations_df,
        data_source_name=data_source_name,
    )

    # filter results to only include facilities which have a location in the
    # reference data source. some facilities may not be in the input if they
    # were filtered out due to sector or emissions reporting period.
    source_facilities = safeguard_facilities_df[safeguard_facilities_df["facility_name"].isin(source_locations["safeguard_facility_name"])]
    source_locations = source_locations[source_locations["safeguard_facility_name"].isin(source_facilities["facility_name"])]

    return source_facilities, source_locations