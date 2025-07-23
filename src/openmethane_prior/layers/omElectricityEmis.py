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
import xarray as xr

from openmethane_prior.config import PriorConfig, load_config_from_env, parse_cli_to_env
from openmethane_prior.outputs import (
    convert_to_timescale,
    add_ch4_total,
    add_sector,
    create_output_dataset,
    write_output_dataset,
)

def processEmissions(config: PriorConfig, prior_ds: xr.Dataset):
    """
    Process emissions from the electricity sector, adding them to the prior
    dataset.
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

    domain_grid = config.domain_grid()

    totalCapacity = sum(item["capacity"] for item in electricityFacilities)

    methane = np.zeros(domain_grid.shape)

    for facility in electricityFacilities:
        cell_coords = domain_grid.lonlat_to_cell_index(facility["lng"], facility["lat"])

        if cell_coords is not None:
            methane[cell_coords[1], cell_coords[0]] += (facility["capacity"] / totalCapacity) * electricityEmis

    add_sector(
        prior_ds=prior_ds,
        sector_name="electricity",
        sector_data=convert_to_timescale(methane, domain_grid.cell_area),
        sector_standard_name="energy_production_and_distribution",
    )


if __name__ == "__main__":
    parse_cli_to_env()
    config = load_config_from_env()

    ds = create_output_dataset(config)
    processEmissions(config, ds)
    add_ch4_total(ds)
    write_output_dataset(config, ds)
