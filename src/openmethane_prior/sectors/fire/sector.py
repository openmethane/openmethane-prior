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

"""Download and process GFAS data

This downloads files from [ADS](https://atmosphere.copernicus.eu/data).
See the project readme for more information about configuring
the required credentials.
"""
import numpy as np
import xarray as xr

from openmethane_prior.lib import (
    PriorSector,
    PriorSectorConfig,
    regrid_dataset,
    logger,
)

from .data_gfas import gfas_data_source

logger = logger.get_logger(__name__)


def process_emissions(sector: PriorSector, sector_config: PriorSectorConfig, prior_ds: xr.Dataset):
    """
    Remap GFAS fire emissions to the CMAQ domain
    """
    config = sector_config.prior_config

    gfas_asset = sector_config.data_manager.get_asset(gfas_data_source)
    gfas_ds = xr.open_dataset(gfas_asset.path)

    # GFAS times are labelled at midnight at the end of the day (i.e. they look
    # like the following day); subtract one day to correct to the actual date
    gfas_ds = gfas_ds.assign_coords(
        valid_time=gfas_ds["valid_time"] - np.timedelta64(1, "D")
    )

    regridded_da = regrid_dataset(
        data_da=gfas_ds["ch4fire"],
        domain_grid=config.domain().grid,
        cache_path=config.intermediates_path,
        cache_name=gfas_asset.name,
    )
    gfas_ds.close()

    result = np.expand_dims(regridded_da.values, 1)  # add single vertical dimension

    return xr.DataArray(
        result,
        coords={
            "time": regridded_da["valid_time"].values,
            "vertical": np.array([1]),
            "y": np.arange(result.shape[-2]),
            "x": np.arange(result.shape[-1]),
        },
    )


sector: PriorSector = PriorSector(
    name="fire",
    emission_category="natural",
    cf_standard_name="fires",
    create_estimate=process_emissions,
)
