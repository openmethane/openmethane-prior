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

@attrs.frozen()
class SectorMeta:
    """
    EmissionsSector describes a methane emission source or sources by name
    and by various classification schemes.
    """
    name: str
    """A machine-friendly sector name that will be used in the name of the
    output variable, like `ch4_sector_{name}`"""

    cf_standard_name: str = None
    """The suffix of the CF Conventions `standard_name` attribute, which will
    be appended to `surface_upward_mass_flux_of_methane_due_to_emission_from_{cf_standard_name}`
    """

    cf_long_name: str = None
    """The CF Conventions `long_name` attribute, if needed."""
