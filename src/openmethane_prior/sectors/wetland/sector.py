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
import datetime
import math
import numpy as np
import pandas as pd
import xarray as xr

from openmethane_prior.lib import (
    DataSource,
    PriorSector,
    PriorSectorConfig,
    logger,
    regrid_dataset,
)

logger = logger.get_logger(__name__)

wetlands_data_source = DataSource(
    name="wetlands",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/DLEM_totflux_CRU_diagnostic.nc",
)

def process_emissions(
    sector: PriorSector,
    sector_config: PriorSectorConfig,
    prior_ds: xr.Dataset,
):
    """Process wetland emissions for the given date range."""
    config = sector_config.prior_config
    domain_grid = config.domain().grid
    wetlands_da = sector_config.data_manager.get_asset(wetlands_data_source)
    wetlands_ds = xr.open_dataset(wetlands_da.path, decode_times=False)

    # input dataset has an improperly formatted time step
    wetlands_start = datetime.date(2000, 1, 1)
    wetlands_months = len(wetlands_ds["time"])
    wetlands_end = datetime.date(2000 + math.floor(wetlands_months / 12), (wetlands_months % 12) + 1, 1)
    wetlands_ds["time"] = xr.date_range(wetlands_start, wetlands_end, freq="M")

    # Regrid all SatWet time steps to the domain grid (no climatology, no unit conversion)
    regridded_da = regrid_dataset(
        data_da=wetlands_ds["totflux"],
        domain_grid=domain_grid,
        lat_dim="lat",
        lon_dim="lon",
        cache_path=config.intermediates_path,
        cache_name=f"{wetlands_da.name}_{prior_ds.domain_name}",
    )
    wetlands_ds.close()

    regridded = regridded_da.values

    # Compute monthly climatology (mean across all years per calendar month) for fallback
    monthly_climatology = {
        month: np.mean(
            regridded[[i for i, t in enumerate(regridded_da['time'].values) if pd.Timestamp(t).month == month]],
            axis=0,
        )
        for month in range(1, 13)
    }

    # Select the monthly climatology for each time step
    result_nd = np.zeros((len(prior_ds["time"]), domain_grid.shape[0], domain_grid.shape[1]))
    for out_idx, date in enumerate(prior_ds["time"].values):
        result_nd[out_idx] = monthly_climatology[pd.Timestamp(date).month]

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
