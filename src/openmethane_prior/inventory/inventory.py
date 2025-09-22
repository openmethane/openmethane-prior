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

import attrs
import calendar
import csv
import datetime
from typing import Iterable

from openmethane_prior.config import PriorConfig
from openmethane_prior.inventory.unfccc import Category, find_category_by_name, is_code_in_code_family, \
    create_category_list
from openmethane_prior.units import days_in_period
from openmethane_prior.logger import get_logger, DuplicateFilter

logger = get_logger(__name__)
# prevent multiple "inventory does not cover YYYY" messages
logger.addFilter(DuplicateFilter())

@attrs.define
class SectorEmission:
    """
    SectorEmission stores a CH4 emission value allocated to a UNFCCC sector.
    """

    unfccc_category: Category
    """UNFCCC sector the emissions are allocated to."""

    ch4_emissions: dict[int, float]
    """Emissions recorded for the sector in kg per annum."""


def kt_to_kg(kilotonnes: float) -> float:
    """Convert measures in kilotonnes to kilograms."""
    return kilotonnes * 1e6


def find_existing_emission(
    emissions_list: list[SectorEmission],
    category: Category,
) -> SectorEmission | None:
    """
    Find an emissions record for a sector in a list of SectorEmissions.
    """
    for emission in emissions_list:
        if emission.unfccc_category == category:
            return emission
    return None


def create_emissions_inventory(
    categories: list[Category],
    inventory_list: Iterable[list[str]],
) -> list[SectorEmission]:
    """
    Create a list of inventory entries, each with annual emissions allocated
    to a UNFCCC sector category code.
    """
    emissions_list = []
    for annual_sector_emission in inventory_list:
        year, level_name_1, level_name_2, level_name_3, level_name_4, level_name_5, emission = annual_sector_emission

        # UNFCCC sector codes / implementation only goes to 4 levels
        level_names = [level_name_1, level_name_2, level_name_3, level_name_4]
        category = find_category_by_name(categories, level_names)
        if category is None:
            raise ValueError(f"Unable to find matching category for: {level_names}")

        sector_emission = find_existing_emission(emissions_list, category)
        if sector_emission is None:
            sector_emission = SectorEmission(unfccc_category=category, ch4_emissions=dict())
            emissions_list.append(sector_emission)

        if not int(year) in sector_emission.ch4_emissions:
            sector_emission.ch4_emissions[int(year)] = 0

        # inventory numbers are in kilotonnes, we want to work in kg
        sector_emission.ch4_emissions[int(year)] += kt_to_kg(float(emission))

    return emissions_list


def get_sector_emissions_by_code(
    emissions_inventory: list[SectorEmission],
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
    year_days = 365 if not calendar.isleap(start_date.year) else 366
    period_annual_fraction = days_in_period(start_date, end_date) / year_days

    aggregated_emission = 0.0
    for emissions in emissions_inventory:
        if is_code_in_code_family(emissions.unfccc_category.code, category_codes):
            inventory_year = start_date.year
            if inventory_year not in emissions.ch4_emissions:
                covered_years = sorted(emissions.ch4_emissions.keys())
                if inventory_year < covered_years[0]:
                    inventory_year = covered_years[0]
                elif inventory_year > covered_years[-1]:
                    inventory_year = covered_years[-1]
                logger.warning(f"inventory does not cover {start_date.year}, using {inventory_year} inventory")

            # reported emissions are for an entire year, take the fraction for
            # the requested time period
            aggregated_emission += emissions.ch4_emissions[inventory_year] * period_annual_fraction

    return aggregated_emission

def load_inventory(config: PriorConfig) -> list[SectorEmission]:
    """Load a CH4 inventory from configured input files"""
    with open(config.as_input_file(config.layer_inputs.unfccc_categories_path), newline='') as codes_file:
        reader = csv.reader(codes_file)
        next(reader) # skip header row
        categories = create_category_list(categories=reader)

    with open(config.as_input_file(config.layer_inputs.inventory_path), newline='') as inventory_file:
        reader = csv.reader(inventory_file)
        next(reader) # skip header row
        return create_emissions_inventory(categories=categories, inventory_list=reader)