#
# Copyright 2023 The Superpower Institute Ltd.
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
import typing
from numpy.typing import ArrayLike

from openmethane_prior.config import PriorConfig

T = typing.TypeVar("T", bound=ArrayLike | float)


def days_in_period(
    start_date: datetime.date,
    end_date: datetime.date,
    inclusive: bool = True,
) -> int:
    """Returns the number of days in the period of days starting at midnight
    at the start of start_date, until midnight at the end of end_date."""
    return (end_date - start_date).days + (1 if inclusive else 0)


SECONDS_PER_DAY = 24 * 60 * 60
def seconds_in_period(start_date: datetime.date, end_date: datetime.date) -> int:
    """Returns the number of seconds in the period of days starting at midnight
    at the start of start_date, until midnight at the end of end_date."""
    return days_in_period(start_date, end_date) * SECONDS_PER_DAY


def kg_to_kg_m2_s(mass_kg: float, area_m2: float, time_s: float) -> float:
    """Convert from total mass, to flux over an area."""
    return mass_kg / area_m2 / time_s


def kg_to_period_cell_flux(mass_kg: T, config: PriorConfig) -> float:
    """Convert from the total emission in a cell over the configured time
    period, to kg/m2/s within the cell."""
    return kg_to_kg_m2_s(
        mass_kg=mass_kg,
        area_m2=config.domain_grid().cell_area,
        time_s=seconds_in_period(config.start_date, config.end_date)
    )

