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

from ..financial_year import FinancialYear


def filter_locations(
    locations_df: pd.DataFrame,
    facility_id: str = None,
    data_source_name: str = None,
    data_source_id: str = None,
):
    """Filter a locations DataFrame by different column values"""
    filtered_df = locations_df.copy()

    if facility_id is not None:
        filtered_df = filtered_df[filtered_df.safeguard_facility_name == facility_id]

    if data_source_name is not None:
        filtered_df = filtered_df[filtered_df.data_source_name == data_source_name]

    if data_source_id is not None:
        filtered_df = filtered_df[filtered_df.data_source_id == data_source_id]

    return filtered_df


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

def filter_locations_for_financial_year(
    locations_df: pd.DataFrame,
    financial_year: FinancialYear,
) -> pd.DataFrame:
    """Keep only the locations which apply in financial_year.

    Location rows may be limited to a range of financial years with the
    optional first_financial_year and last_financial_year columns, holding
    labels like "2024-25". A missing value leaves that side of the range open.
    This allows, for example, a facility which absorbed another facility to
    include the absorbed facility's location only from the year it was
    absorbed.

    Raises
    ------
    ValueError
        If a financial year label is invalid, or a row's first financial year
        is after its last.
    """
    def start_years(column: str) -> pd.Series:
        if column not in locations_df.columns:
            return pd.Series(pd.NA, index=locations_df.index, dtype="Int64")
        return locations_df[column].map(
            lambda label: pd.NA if pd.isna(label) or str(label).strip() == ""
            else FinancialYear.from_label(str(label)).start_year
        ).astype("Int64")

    first_years = start_years("first_financial_year")
    last_years = start_years("last_financial_year")

    reversed_mask = (first_years > last_years).fillna(False)
    if reversed_mask.any():
        facilities = sorted(locations_df.loc[reversed_mask, "safeguard_facility_name"].unique())
        raise ValueError(
            f"Safeguard locations have a first financial year after their last: {facilities}"
        )

    start_year = financial_year.start_year
    in_year_mask = (first_years.isna() | (first_years <= start_year)) & (
        last_years.isna() | (start_year <= last_years)
    )
    return locations_df[in_year_mask.astype(bool)]
