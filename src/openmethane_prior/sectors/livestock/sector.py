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

from openmethane_prior.lib import (
    DataSource,
    convert_to_timescale,
    logger,
    PriorSector,
    PriorSectorConfig,
)

logger = logger.get_logger(__name__)

livestock_data_source = DataSource(
    name="enteric-fermentation",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/EntericFermentation.nc",
)

def process_emissions(
    sector: PriorSector,
    sector_config: PriorSectorConfig,
    prior_ds: xr.Dataset,
):
    config = sector_config.prior_config

    livestock_asset = sector_config.data_manager.get_asset(livestock_data_source)
    with xr.open_dataset(livestock_asset.path) as lss:
        ls = lss.load()

    domain_grid = config.domain_grid()

    # Re-project into domain coordinates
    # - create meshgrids of the lats and lons
    lonmesh, latmesh = np.meshgrid(ls.lon, ls.lat)
    cell_x, cell_y, cell_valid = domain_grid.lonlat_to_cell_index(lonmesh, latmesh)

    enteric_as_array = lss.CH4_total.to_numpy()

    livestockCH4 = np.zeros(domain_grid.shape)
    logger.info("Distribute livestock CH4 (long process)")
    # we're accumulating emissions from fine to coarse grid
    # accumulate in mass units and divide by area at end
    for j in range(ls.lat.size):
        ix, iy = cell_x[j,:], cell_y[j,:]
        # input domain is bigger so mask indices out of range
        mask = cell_valid[j, :]
        if mask.any():
            # the following needs to use .at method since iy,ix indices may be repeated and we need to acumulate
            np.add.at(livestockCH4, (iy[mask], ix[mask]), enteric_as_array[j, mask])

    return convert_to_timescale(livestockCH4, domain_grid.cell_area)


sector = PriorSector(
    name="livestock",
    emission_category="anthropogenic",
    unfccc_categories=["3.A"], # Enteric Fermentation
    cf_standard_name="domesticated_livestock",
    create_estimate=process_emissions,
)
