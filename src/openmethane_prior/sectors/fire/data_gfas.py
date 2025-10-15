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

import cdsapi
import pathlib

from openmethane_prior.lib import (
    ConfiguredDataSource,
    DataSource,
    PriorConfig,
)

def gfas_file_name(data_source: DataSource, prior_config: PriorConfig) -> str:
    return f"gfas_{prior_config.start_date.strftime('%Y-%m-%d')}_{prior_config.end_date.strftime('%Y-%m-%d')}.nc"

def gfas_fetch(data_source: ConfiguredDataSource) -> pathlib.Path:
    """
    Download GFAS methane between start and end date, returning the filename
    of the retrieved data.
    """
    start_date_fmt = data_source.prior_config.start_date.strftime('%Y-%m-%d')
    end_date_fmt = data_source.prior_config.end_date.strftime('%Y-%m-%d')

    c = cdsapi.Client(progress=False)
    c.retrieve(
        "cams-global-fire-emissions-gfas",
        {
            "date": f"{start_date_fmt}/{end_date_fmt}",
            "format": "netcdf",
            "variable": [
                "wildfire_flux_of_methane",
            ],
        },
        data_source.asset_path,
    )

    return data_source.asset_path

gfas_data_source = DataSource(
    name="gfas",
    file_path=gfas_file_name,
    fetch=gfas_fetch,
)