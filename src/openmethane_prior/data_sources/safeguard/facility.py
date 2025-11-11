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
from typing import Iterable

import attrs
import re

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
        return None
    return anzsic_code.group('code')

def create_facility_from_safeguard_record(
    record: SafeguardFacilityRecord,
    ch4_co2e_factor: float,
) -> SafeguardFacility:
    """Create a SafeguardFacility object from a single row of the Baselines and
    Emissions Table. CH4 must be converted from tCO2-equivalent to kg CH4."""
    return SafeguardFacility(
        name=record.facility_name,
        state=record.state,
        anzsic=record.anzsic,
        anzsic_code=parse_anzsic_code(record.anzsic),
        ch4_emissions=dict({
            "2023-2024": record.co2e_ch4 * 1000 / ch4_co2e_factor, # tCO2e to kg
        }),
    )

def find_existing_facility(
    facility_list: list[SafeguardFacility],
    search_facility: SafeguardFacility,
) -> SafeguardFacility | None:
    """Find a matching facility in the provided list, if present."""
    for facility in facility_list:
        if facility.name == search_facility.name:
            return facility
    return None

def create_facility_list(
    facility_records: Iterable[SafeguardFacilityRecord],
    ch4_co2e_factor: float,
) -> list[SafeguardFacility]:
    """Construct a searchable list of facilities and their emissions from the
    raw input records."""
    facility_list: list[SafeguardFacility] = []
    for record in facility_records:
        new_facility = create_facility_from_safeguard_record(record, ch4_co2e_factor)
        existing = find_existing_facility(facility_list, new_facility)
        if existing is None:
            facility_list.append(new_facility)
        else:
            # each facility should be represented only once in our list. if a
            # facility appears multiple times in the dataset, aggregate all of
            # its reported emissions.
            for period in existing.ch4_emissions.keys():
                existing.ch4_emissions[period] += new_facility.ch4_emissions[period]
    return facility_list
