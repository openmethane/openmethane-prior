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

from openmethane_prior.data_sources.inventory import inventory_domain_data_source
from openmethane_prior.lib import (
    ConfiguredDataSource,
    DataSource,
    Domain,
    GriddedProxy,
)


def parse_ntlt_data_source(data_source: ConfiguredDataSource) -> GriddedProxy:
    prior_config = data_source.prior_config
    domain = prior_config.domain()
    inventory_domain: Domain = data_source.data_assets[0].data

    ntlData = rxr.open_rasterio(data_source.asset_path, masked=False)

    # sum over three bands
    ntlt = ntlData.sum(axis=0)
    np.nan_to_num(ntlt, copy=False)

    return GriddedProxy.from_raster(
        raster=ntlt,
        domain_grid=domain.grid,
        inventory_domain=inventory_domain,
    )


night_lights_data_source = DataSource(
    name="nighttime-lights",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/nasa-nighttime-lights.tiff",
    parse=parse_ntlt_data_source,
    data_sources=[inventory_domain_data_source],
)
