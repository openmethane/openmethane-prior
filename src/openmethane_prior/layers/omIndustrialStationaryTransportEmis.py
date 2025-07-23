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

"""Processing industrial stationary transport emissions"""

import numpy as np
import pandas as pd
import rioxarray as rxr
import xarray as xr

from openmethane_prior.config import PriorConfig, load_config_from_env, parse_cli_to_env
from openmethane_prior.outputs import (
    convert_to_timescale,
    add_ch4_total,
    add_sector,
    create_output_dataset,
    write_output_dataset,
)
from openmethane_prior.raster import remap_raster

sectorEmissionStandardNames = {
    "industrial": "industrial_processes_and_combustion",
    "stationary": "industrial_energy_production",
    "transport": "land_transport",
}


def processEmissions(config: PriorConfig, prior_ds: xr.Dataset):
    """
    Process emissions for Industrial, Stationary and Transport sectors, adding
    them to the prior dataset.
    """
    print("processEmissions for Industrial, Stationary and Transport")

    sectorsUsed = ["industrial", "stationary", "transport"]

    ntlData = rxr.open_rasterio(
        config.as_input_file(config.layer_inputs.ntl_path), masked=False
    )
    # sum over three bands
    ntlt = ntlData.sum(axis=0)
    np.nan_to_num(ntlt, copy=False)

    om_ntlt = remap_raster(ntlt, config, AREA_OR_POINT=ntlData.AREA_OR_POINT)

    # apply land mask before counting any night lights
    om_ntlt = om_ntlt * prior_ds["land_mask"]

    # we want proportions of total for scaling emissions
    ntltScalar = om_ntlt/om_ntlt.sum()
    sectorData = pd.read_csv(
        config.as_input_file(config.layer_inputs.sectoral_emissions_path)
    ).to_dict(orient="records")[0]
    methane = {}
    for sector in sectorsUsed:
        methane[sector] = ntltScalar * sectorData[sector] * 1e9
        add_sector(
            prior_ds=prior_ds,
            sector_name=sector.lower(),
            sector_data=convert_to_timescale(methane[sector], config.domain_grid().cell_area),
            sector_standard_name=sectorEmissionStandardNames[sector],
        )


if __name__ == "__main__":
    parse_cli_to_env()
    config = load_config_from_env()

    ds = create_output_dataset(config)
    processEmissions(config, ds)
    add_ch4_total(ds)
    write_output_dataset(config, ds)
