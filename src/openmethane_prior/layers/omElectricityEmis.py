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

"""Process emissions from the electricity sector"""

import numpy as np
import pandas as pd

from openmethane_prior.config import PriorConfig, load_config_from_env
from openmethane_prior.outputs import convert_to_timescale, sum_layers, write_layer
from openmethane_prior.utils import domain_cell_index


def processEmissions(config: PriorConfig):
    """
    Process emissions from the electricity sector

    Adds `OCH4_ELECTRICITY` layer to the output file
    """
    print("processEmissions for Electricity")

    electricityEmis = (
        pd.read_csv(config.as_input_file(config.layer_inputs.sectoral_emissions_path)).to_dict(
            orient="records"
        )[0]["electricity"]
        * 1e9
    )
    electricityFacilities = pd.read_csv(
        config.as_input_file(config.layer_inputs.electricity_path), header=0
    ).to_dict(orient="records")

    domain_ds = config.domain_dataset()

    totalCapacity = sum(item["capacity"] for item in electricityFacilities)
    landmask = domain_ds["LANDMASK"][:]

    _, lmy, lmx = landmask.shape

    methane = np.zeros(landmask.shape)

    # Get the routine to project the lat/lon grid on to the project grid
    for facility in electricityFacilities:
        ix, iy = domain_cell_index(config, facility["lng"], facility["lat"])
        try:
            methane[0][iy][ix] += (facility["capacity"] / totalCapacity) * electricityEmis
        except IndexError:
            pass  # it's outside our domain

    write_layer(
        config.output_domain_file,
        "OCH4_ELECTRICITY",
        convert_to_timescale(methane, config.domain_cell_area),
        config=config,
    )


if __name__ == "__main__":
    config = load_config_from_env()
    processEmissions(config)
    sum_layers(config.output_domain_file)
