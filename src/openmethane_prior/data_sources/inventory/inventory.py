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
import calendar
import datetime

import pandas as pd

from openmethane_prior.lib.units import days_in_period
from openmethane_prior.lib.logger import get_logger

from .unfccc import is_code_in_code_family

logger = get_logger(__name__)


def kt_to_kg(kilotonnes):
    """Convert measures in kilotonnes to kilograms."""
    return kilotonnes * 1e6


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
    if start_date.year != end_date.year:
        raise ValueError("periods spanning multiple years are not supported")

    # find inventory data for the referenced year, or if the period of interest
    # is outside the covered period, use the closest available year
    inventory_year = start_date.year
    covered_years = emissions_inventory["InventoryYear_ID"].unique()
    covered_years.sort()
    if inventory_year not in covered_years:
        logger.warning(f"inventory does not cover {start_date.year}, using {inventory_year} inventory")
        if inventory_year < covered_years[0]:
            inventory_year = covered_years[0]
        elif inventory_year > covered_years[-1]:
            inventory_year = covered_years[-1]

    year_days = 365 if not calendar.isleap(inventory_year) else 366
    period_annual_fraction = days_in_period(start_date, end_date) / year_days

    year_df = emissions_inventory[emissions_inventory["InventoryYear_ID"] == inventory_year]

    code_match_check = lambda unfccc_code: is_code_in_code_family(unfccc_code, category_codes)
    code_match_mask = year_df["UNFCCC_Code"].map(code_match_check)

    aggregated_emission = year_df[code_match_mask]["ch4_kg"].sum()

    return aggregated_emission * period_annual_fraction
