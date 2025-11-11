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

from .sector import PriorSector


@attrs.define
class AustraliaPriorSector(PriorSector):
    """
    AustraliaPriorSector augments PriorSector with attributes that assist
    constructing emission estimates that are specific to Australian datasets.
    """

    anzsic_codes: list[str] = attrs.field(default=None)
    """List of ANZSIC classification codes for sectors which are represented in
    the emissions. Codes must start with a Subdivision, Group and Class are
    optional. Codes must not include Division, i.e.:
    - ["060", "07", "1111"] # valid
    """
    @anzsic_codes.validator
    def check_anzsic_codes(self, attribute, value):
        if value is not None:
            for code in value:
                if len(code) < 2:
                    raise ValueError(f"anzsic code '{code}' is not a valid subdivision")

        if self.emission_category == "natural" and value is not None:
            raise ValueError("natural emissions cannot have anzsic_codes")
