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

"""Processing termite Methane emissions"""

import xarray as xr

from openmethane_prior.lib import (
    DataSource,
    PriorSector,
    PriorSectorConfig,
    regrid_data_array_conservative,
)
from openmethane_prior.lib.utils import SECS_PER_YEAR

termites_data_source = DataSource(
    name="termites",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/termite_emissions_2010-2016.nc",
)


def process_emissions(
    sector: PriorSector,
    sector_config: PriorSectorConfig,
    prior_ds: xr.Dataset,
):
    """Remap termite emissions to the CMAQ domain"""
    config = sector_config.prior_config

    termites_asset = sector_config.data_manager.get_asset(termites_data_source)
    ds = xr.open_dataset(termites_asset.path)

    # negative values indicate missing data; input is mtCH4/gridcell/yr (extensive)
    flux = ds["ch4_emissions_2010_2016.asc"].fillna(0.0).clip(min=0.0)
    ds.close()

    # extensive=True normalises by source cell area inside regrid_data_array_conservative,
    # so the output is in mtCH4/m²
    result_nd = regrid_data_array_conservative(
        data_da=flux,
        domain_grid=config.domain().grid,
        cache_path=config.intermediates_path,
        cache_name=f"{termites_asset.name}_{prior_ds.domain_name}",
        lat_dim="lat",
        lon_dim="lon",
        extensive=True,
    ).values

    # convert from mtCH4/m²/year → kg/m²/s
    result_nd *= 1e9 / SECS_PER_YEAR

    # apply land mask to exclude termite emissions over ocean
    land_mask = prior_ds["land_mask"].to_numpy()
    result_nd *= land_mask

    return result_nd


sector = PriorSector(
    name="termite",
    emission_category="natural",
    cf_standard_name="termites",
    create_estimate=process_emissions,
)
