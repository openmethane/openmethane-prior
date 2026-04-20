#
# Copyright 2025 The Superpower Institute Ltd.
#
# This file is part of Open Methane.
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
import pandas as pd

from openmethane_prior.lib.units import days_in_period
from openmethane_prior.lib.logger import get_logger

from .unfccc import is_code_in_code_family

logger = get_logger(__name__)

_LEVEL_COLUMNS = ["UNFCCC_Level_1", "UNFCCC_Level_2", "UNFCCC_Level_3", "UNFCCC_Level_4"]

def kt_to_kg(kilotonnes):
    """Convert measures in kilotonnes to kilograms."""
    return kilotonnes * 1e6


"""ANGA inventories follow the Australian financial year, which goes from July
1st - June 30th of the following year. In their API, ANGA specifies a single
year indicating the end year of the financial year for that data. I.e. "2023"
references the "2022/2023" financial year."""
def financial_year_start(year: int) -> datetime.datetime:
    """Return the start date of an ANGA inventory financial year."""
    return datetime.datetime(year - 1, 7, 1)

def financial_year_end(year: int) -> datetime.datetime:
    """Return the end date of an ANGA inventory financial year."""
    return datetime.datetime(year, 6, 30) + datetime.timedelta(hours=24)

def financial_year_from_date(date: datetime.date) -> int:
    """Return the ANGA inventory financial year a date falls in."""
    return date.year + 1 if date.month >= 7 else date.year


def create_inventory_df(anga_inventory_records, unfccc_df: pd.DataFrame) -> pd.DataFrame:
    anga_df = pd.DataFrame.from_records(
        anga_inventory_records,
        columns=[
            "InventoryYear_ID",
            "UNFCCC_Level_1", "UNFCCC_Level_2", "UNFCCC_Level_3", "UNFCCC_Level_4",
            "Gas_Level_0",
            "Gg",
        ],
    )

    # Filter out non-CH4 emissions
    anga_df = anga_df[anga_df["Gas_Level_0"] == "CH4"]

    # Convert kt to kg
    anga_df["ch4_kg"] = kt_to_kg(anga_df["Gg"])

    # Add UNFCCC code column using cascading fallback: try all 4 levels first,
    # then progressively drop the most specific level until a match is found.
    anga_df["UNFCCC_Code"] = anga_df.apply(_find_unfccc_code, axis=1, unfccc_df=unfccc_df)

    return anga_df


def _find_unfccc_code(row: pd.Series, unfccc_df: pd.DataFrame) -> str | None:
    """Find the closest UNFCCC code for a single ANGA row.

    Tries to match on all 4 levels first, then progressively drops the most
    specific level, only considering unfccc_df rows where the dropped levels
    are empty (i.e. parent categories).
    """
    for n_levels in range(len(_LEVEL_COLUMNS), 0, -1):
        mask = pd.Series(True, index=unfccc_df.index)
        for col in _LEVEL_COLUMNS[:n_levels]:
            mask &= unfccc_df[col] == row[col]
        for col in _LEVEL_COLUMNS[n_levels:]:
            mask &= unfccc_df[col].isna() | (unfccc_df[col] == "")
        matches = unfccc_df[mask]
        if not matches.empty:
            if n_levels < len(_LEVEL_COLUMNS):
                logger.debug(f"Used {n_levels}-level match for {[row[c] for c in _LEVEL_COLUMNS]}")
            return matches.iloc[0]["UNFCCC_Code"]
    raise ValueError(f"No matching UNFCCC code for inventory row: {row}")


def get_sector_emissions_by_code(
    emissions_inventory: pd.DataFrame,
    category_codes: list[str],
    start_date: datetime.date,
    end_date: datetime.date,
) -> float:
    """
    Find and aggregate emissions across all child sectors which sit within the
    provided category code. If a parent category like "1" (Energy) is provided,
    then the returned value will include all emissions for every sector within
    Energy.
    """
    inventory_year = financial_year_from_date(start_date)
    if financial_year_from_date(end_date) != inventory_year:
        raise ValueError(
            f"start_date ({start_date}) and end_date ({end_date}) must be within the same financial year"
        )

    # Build a sorted table of unique inventory years with their period boundaries
    year_periods: list[int] = list(
        emissions_inventory["InventoryYear_ID"].drop_duplicates().astype(int).sort_values()
    )

    if inventory_year not in year_periods:
        inventory_year = year_periods[-1] if inventory_year > year_periods[-1] else year_periods[0]
        logger.warning(
            f"inventory does not cover {start_date}, using {inventory_year} inventory"
        )

    year_days = (financial_year_end(inventory_year) - financial_year_start(inventory_year)).days
    period_annual_fraction = days_in_period(start_date, end_date) / year_days

    year_df = emissions_inventory[emissions_inventory["InventoryYear_ID"] == inventory_year]

    code_match_check = lambda unfccc_code: is_code_in_code_family(unfccc_code, category_codes)
    code_match_mask = year_df["UNFCCC_Code"].map(code_match_check)

    aggregated_emission = year_df[code_match_mask]["ch4_kg"].sum()

    return aggregated_emission * period_annual_fraction
