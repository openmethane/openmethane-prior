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
from __future__ import annotations

import attrs
from collections.abc import Callable
import numpy as np
import xarray as xr

from .config import PriorSectorConfig

emission_categories = [
    "natural", # originating in natural processes
    "anthropogenic", # originating in human activity
]

@attrs.define
class PriorSector:
    """
    SectorMeta describes a methane emission source or sources by name
    and by various classification schemes.
    """
    name: str
    """A machine-friendly sector name that will be used in the name of the
    output variable, like `ch4_sector_{name}`"""

    create_estimate: Callable[[PriorSector, PriorSectorConfig, xr.Dataset], xr.DataArray | np.ndarray]
    """A method to create the emissions estimate for the sector based on the
    parameters specified in PriorSectorConfig.
    
    The sector output should be added as a layer to provided Dataset using the
    add_sector method.
    """

    emission_category: str = attrs.field()
    """The origin or cause of the emissions. Valid values are:
      - natural
      - anthropogenic
    """
    @emission_category.validator
    def check_emission_category(self, attribute, value):
        if value not in emission_categories:
            raise ValueError(f"emission_category must be one of {', '.join(emission_categories)}")


    unfccc_categories: list[str] = attrs.field(default=None)
    """List of UNFCCC CRT category codes for sectors which are represented in
    the emissions.
    """
    @unfccc_categories.validator
    def check_unfccc_categories(self, attribute, value):
        if self.emission_category == "natural" and value is not None:
            raise ValueError("natural emissions cannot have unfccc_categories")
        if self.emission_category == "anthropogenic" and (value is None or len(value) == 0):
            raise ValueError("anthropogenic emissions must have a value in unfccc_categories")

    cf_standard_name: str = None
    """The suffix of the CF Conventions `standard_name` attribute, which will
    be appended to `surface_upward_mass_flux_of_methane_due_to_emission_from_{cf_standard_name}`
    """

    cf_long_name: str = None
    """The CF Conventions `long_name` attribute, if needed."""
