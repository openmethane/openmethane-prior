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
from openmethane_prior.config import PriorConfig, load_config_from_env
from openmethane_prior.outputs import (
    convert_to_timescale,
    sum_layers,
    write_layer,
)
from openmethane_prior.raster import remap_raster


def processEmissions(config: PriorConfig):
    """
    Process emissions for Industrial, Stationary and Transport

    Writes layers into the output file
    """
    print("processEmissions for Industrial, Stationary and Transport")

    sectors_used = ["industrial", "stationary", "transport"]

    ntl_data = rxr.open_rasterio(config.as_input_file(config.layer_inputs.ntl_path), masked=False)
    # sum over three bands
    ntlt = ntl_data.sum(axis=0)
    np.nan_to_num(ntlt, copy=False)

    om_ntlt = remap_raster(ntlt, config, AREA_OR_POINT=ntl_data.AREA_OR_POINT)
    # we want proportions of total for scaling emissions
    ntlt_scalar = om_ntlt / om_ntlt.sum()
    sector_data = pd.read_csv(
        config.as_input_file(config.layer_inputs.sectoral_emissions_path)
    ).to_dict(orient="records")[0]
    methane = {}
    for sector in sectors_used:
        methane[sector] = ntlt_scalar * sector_data[sector] * 1e9
        write_layer(
            config.output_domain_file,
            f"OCH4_{sector.upper()}",
            convert_to_timescale(methane[sector], config.domain_cell_area),
            config=config,
        )


if __name__ == "__main__":
    config = load_config_from_env()
    processEmissions(config)
    sum_layers(config.output_domain_file)
