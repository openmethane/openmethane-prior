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
import rioxarray as rxr

from openmethane_prior.lib import (
    ConfiguredDataSource,
    DataSource,
    regrid_data,
    remap_raster,
)


def parse_ntlt_data_source(data_source: ConfiguredDataSource):
    prior_config = data_source.prior_config
    ntlData = rxr.open_rasterio(data_source.asset_path, masked=False)

    # sum over three bands
    ntlt = ntlData.sum(axis=0)
    np.nan_to_num(ntlt, copy=False)

    om_ntlt = remap_raster(ntlt, prior_config.domain_grid())

    # limit emissions to land points
    inventory_mask_regridded = regrid_data(prior_config.inventory_dataset()['inventory_mask'], from_grid=prior_config.inventory_grid(), to_grid=prior_config.domain_grid())
    om_ntlt *= inventory_mask_regridded

    # now collect total nightlights across inventory domain
    inventory_ntlt = remap_raster(ntlt, prior_config.inventory_grid())

    # now mask to region of inventory
    inventory_ntlt *= prior_config.inventory_dataset()['inventory_mask']

    # we want proportions of total for scaling emissions
    return om_ntlt / inventory_ntlt.sum().item()


night_lights_data_source = DataSource(
    name="nighttime-lights",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/nasa-nighttime-lights.tiff",
    parse=parse_ntlt_data_source,
)
