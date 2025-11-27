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
import datetime

import attrs
import re

import numpy as np
import pandas as pd

from openmethane_prior.data_sources.safeguard.anzsic import simplify_anzsic_code


@attrs.define()
class SafeguardFacility:
    name: str
    """Facility name as present in the Safeguard Mechanism Baselines and Emissions Table"""

    state: str
    """State or territory where the facility operates"""

    anzsic: str
    """Full ANZSIC description as present in the Safeguard Mechanism, like:
      - Coal mining (060)
      - Oil and gas extraction (070)
    """

    anzsic_code: str
    """ANZSIC code, like 060 or 070"""

    ch4_emissions: dict[str, float]
    """Emissions reported for the facility in kg CH4 per annum.
    
    The dictionary key is an Australian financial year like "2023-2024", which
    represents the period from July 1st in the starting year to June 30th the
    following year."""


@attrs.define()
class SafeguardFacilityRecord:
    """A single row read from the Safeguard Mechanism Emissions Table"""
    facility_name: str
    business_name: str
    state: str
    anzsic: str
    co2e_ch4: float


anzsic_code_pattern = re.compile("\((?P<code>\d+)\)$")
def parse_anzsic_code(anzsic_full: str) -> str:
    """Given a full ANZSIC description like "Coal mining (060)", extract the
    code, i.e. "060"."""
    anzsic_code = anzsic_code_pattern.search(anzsic_full)
    if anzsic_code is None:
        raise ValueError(f"invalid ANZSIC string has no code '{anzsic_full}'")
    return anzsic_code.group('code')


def create_facilities_from_safeguard_rows(
    safeguard_rows_df: pd.DataFrame,
    reporting_period: tuple[int, int],
    ch4_gwp: float,
    co2_gwp: float = 1,
) -> pd.DataFrame:
    """Create a SafeguardFacility object from a single row of the Baselines and
    Emissions Table. CH4 must be converted from CO2-equivalent kg to CH4 kg."""
    safeguard_df = safeguard_rows_df.copy()

    # rows with the same facility name but different business name are the same
    # facility, and should have their CH4 aggregated. this sums co2e_ch4 while
    # preserving other columns.
    safeguard_df = safeguard_df.groupby(["facility_name", "state", "anzsic"], as_index=False).sum()

    # convert tCO2e CH4 to kg CH4 using global warming potentials
    safeguard_df["ch4_kg"] = safeguard_df["co2e_ch4"] * 1000 * (co2_gwp / ch4_gwp)

    # extract the ANZSIC code from the provided format
    safeguard_df["anzsic_code"] = safeguard_df["anzsic"].map(parse_anzsic_code)

    # SGM reporting follows Australian financial year, from
    # July 1st to June 30 the following year
    reporting_start_year, reporting_end_year = reporting_period
    safeguard_df["reporting_start"] = datetime.date(reporting_start_year, 7, 1)
    safeguard_df["reporting_end"] = datetime.date(reporting_end_year, 6, 30)

    return safeguard_df


def filter_facilities(
    facility_df: pd.DataFrame,
    anzsic_codes: list[str] = None,
    period: tuple[datetime.date, datetime.date] = None,
) -> pd.DataFrame:
    """Filter safeguard mechanism rows, returning facilities which match the
    provided sector and period filters."""
    if anzsic_codes is not None:
        anzsic_prefixes = [simplify_anzsic_code(anzsic) for anzsic in anzsic_codes]
        # filter to include every row where the ANZSIC code matches any prefix
        facility_df = facility_df[np.logical_or.reduce([
            facility_df["anzsic_code"].str.startswith(anzsic_prefix)
            for anzsic_prefix in anzsic_prefixes
        ])]

    if period is not None:
        facility_df = facility_df[
            (facility_df["reporting_start"] <= period[0])
            & (period[1] <= facility_df["reporting_end"])
        ]

    return facility_df
