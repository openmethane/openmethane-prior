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

import attrs

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
    """Emissions reported for the facility in kg per annum.
    
    The dictionary key is an Australian financial year like "2023-2024", which
    represents the period from July 1st in the starting year to June 30th the
    following year."""

