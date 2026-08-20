#
# Copyright 2023 The Superpower Institute Ltd.
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
import numpy as np
import xarray as xr

from openmethane_prior.lib.units import SECONDS_PER_DAY
from openmethane_prior.lib.verification import sector_period_total

CELL_AREA = 100.0
PERIOD_DAYS = 7


def test_sector_period_total_time_resolved():
    """A layer with one value per day is already totalled over the period."""
    flux = np.full((PERIOD_DAYS, 1, 2, 2), 3.0)
    sector_data = xr.DataArray(flux, dims=["time", "vertical", "y", "x"])

    total = sector_period_total(sector_data, cell_area=CELL_AREA, period_days=PERIOD_DAYS)

    # 4 cells x 7 days x 3 kg/m2/s
    assert total == 4 * PERIOD_DAYS * 3.0 * CELL_AREA * SECONDS_PER_DAY


def test_sector_period_total_time_invariant():
    """A layer stored without a time dimension is scaled up to the whole period."""
    flux = np.full((1, 2, 2), 3.0)
    sector_data = xr.DataArray(flux, dims=["vertical", "y", "x"])

    total = sector_period_total(sector_data, cell_area=CELL_AREA, period_days=PERIOD_DAYS)

    assert total == 4 * PERIOD_DAYS * 3.0 * CELL_AREA * SECONDS_PER_DAY


def test_sector_period_total_matches_duplicated_layer():
    """Storing one estimate must total the same as repeating it for every day.

    This is the invariant that keeps verify_emis comparable to the inventory
    now that time-invariant sectors are no longer duplicated across time.
    """
    rng = np.random.default_rng(seed=0)
    flux = rng.random((1, 5, 4))

    time_invariant = xr.DataArray(flux, dims=["vertical", "y", "x"])
    duplicated = xr.DataArray(
        np.concatenate([flux[np.newaxis, ...]] * PERIOD_DAYS, axis=0),
        dims=["time", "vertical", "y", "x"],
    )

    assert sector_period_total(
        time_invariant, cell_area=CELL_AREA, period_days=PERIOD_DAYS
    ) == sector_period_total(duplicated, cell_area=CELL_AREA, period_days=PERIOD_DAYS)
