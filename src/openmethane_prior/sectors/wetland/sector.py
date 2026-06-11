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

"""Processing wetland emissions"""
import calendar
import numpy as np
import pandas as pd
import xarray as xr

from openmethane_prior.lib import (
    DataSource,
    PriorSector,
    PriorSectorConfig,
    logger,
    regrid_data_array_conservative,
)
from openmethane_prior.lib.units import SECONDS_PER_DAY

logger = logger.get_logger(__name__)

satwet_giems_data_source = DataSource(
    name="SatWet-GIEMS",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/SatWetCH4_GIEMS-MC_v2-90.nc",
)

def process_emissions(
    sector: PriorSector,
    sector_config: PriorSectorConfig,
    prior_ds: xr.Dataset,
):
    """Process wetland emissions for the given date range."""
    config = sector_config.prior_config
    domain_grid = config.domain().grid
    wetlands_da = sector_config.data_manager.get_asset(satwet_giems_data_source)
    wetlands_ds = xr.open_dataset(wetlands_da.path)

    # SatWet time coordinates are first-of-month; compare at (year, month) granularity
    wetlands_time = wetlands_ds["time"].values
    wetlands_min_dt = pd.Timestamp(wetlands_time.min())
    wetlands_max_dt = pd.Timestamp(wetlands_time.max())
    wetlands_min_ym = (wetlands_min_dt.year, wetlands_min_dt.month)
    wetlands_max_ym = (wetlands_max_dt.year, wetlands_max_dt.month)

    start_date = sector_config.prior_config.start_date
    end_date = sector_config.prior_config.end_date
    start_ym = (start_date.year, start_date.month)
    end_ym = (end_date.year, end_date.month)

    # Regrid all SatWet time steps to the domain grid (no climatology, no unit conversion)
    regridded_da = regrid_data_array_conservative(
        data_da=wetlands_ds["fch4_mean"],
        domain_grid=domain_grid,
        cache_path=config.intermediates_path,
        cache_name=f"{wetlands_da.name}_{prior_ds.domain_name}",
    )
    wetlands_ds.close()

    regridded = regridded_da.values

    # Convert units: gCH4/m2/month → kg/m2/s using the actual year+month per time step
    for t_idx, t in enumerate(wetlands_time):
        dt = pd.Timestamp(t)
        _, days_in_month = calendar.monthrange(dt.year, dt.month)
        regridded[t_idx] /= 1000.0 * days_in_month * SECONDS_PER_DAY

    # Build (year, month) → index lookup for O(1) time-step selection
    satwet_index = {
        (pd.Timestamp(t).year, pd.Timestamp(t).month): i
        for i, t in enumerate(wetlands_time)
    }

    # If the period of interest lies outside the range of dates in the input
    # data, compute monthly climatology (mean across all years per calendar
    # month) to use as a fallback.
    monthly_climatology = None
    if start_ym < wetlands_min_ym or end_ym > wetlands_max_ym:
        logger.info(
            "Requested period %s - %s extends outside the SatWet data range %s - %s; "
            "monthly climatology will be used for out-of-range months.",
            start_date,
            end_date,
            wetlands_min_dt,
            wetlands_max_dt,
        )

        monthly_climatology = {
            month: np.mean(
                regridded[[i for i, t in enumerate(regridded_da['time'].values) if pd.Timestamp(t).month == month]],
                axis=0,
            )
            for month in range(1, 13)
        }

    # Select the monthly emissions for each time step. If the time step falls
    # outside the monthly results, use climatology for that calendar month.
    result_nd = np.zeros((len(prior_ds["time"]), domain_grid.shape[0], domain_grid.shape[1]))
    for out_idx, date in enumerate(prior_ds["time"].values):
        dt = pd.Timestamp(date)
        ym = (dt.year, dt.month)
        if ym in satwet_index:
            result_nd[out_idx] = regridded[satwet_index[ym]]
        else:
            if monthly_climatology is None:
                raise ValueError("Climatology was not calculated despite out of bounds time step")
            result_nd[out_idx] = monthly_climatology[dt.month]

    # source dataset is a coarse grid, and has emissions over ocean which
    # definitely shouldn't be classified as wetlands
    land_mask = prior_ds['land_mask'].to_numpy()
    result_nd *= land_mask

    result_nd = np.expand_dims(result_nd, 1)  # adding single vertical dimension

    return xr.DataArray(
        result_nd,
        coords={
            "time": prior_ds["time"].values,
            "vertical": np.array([1]),
            "y": np.arange(result_nd.shape[-2]),
            "x": np.arange(result_nd.shape[-1]),
        },
    )


sector = PriorSector(
    name="wetlands",
    emission_category="natural",
    cf_standard_name="wetland_biological_processes",
    create_estimate=process_emissions,
)
