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

from openmethane_prior.lib import PriorSector

from .agriculture import sector as agriculture_sector
from .coal import sector as coal_sector
from .electricity import sector as electricity_sector
from .fire import sector as fire_sector
from .industrial import sector as industrial_sector
from .livestock import sector as livestock_sector
from .lulucf import sector as lulucf_sector
from .oil_gas import sector as oil_gas_sector
from .stationary import sector as stationary_sector
from .termite import sector as termite_sector
from .transport import sector as transport_sector
from .waste import sector as waste_sector
from .wetland import sector as wetland_sector

all_sectors: list[PriorSector] = [
    agriculture_sector,
    coal_sector,
    electricity_sector,
    fire_sector,
    industrial_sector,
    livestock_sector,
    lulucf_sector,
    oil_gas_sector,
    stationary_sector,
    termite_sector,
    transport_sector,
    waste_sector,
    wetland_sector,
]
