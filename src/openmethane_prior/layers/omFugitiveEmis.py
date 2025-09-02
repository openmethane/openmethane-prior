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

"""Process fugitive Methane emissions"""

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
import openmethane_prior.logger as logger
from openmethane_prior.sector.sector import SectorMeta

logger = logger.get_logger(__name__)

sector_meta = SectorMeta(
    name="fugitive",
    natural=False,
    cf_standard_name="extraction_production_and_transport_of_fuel",
)

def processEmissions(config: PriorConfig, prior_ds: xr.Dataset):
    """
    Process the fugitive methane emissions

    Adds the ch4_fugitive layer to the output
    """
    logger.info("processEmissions for fugitives")
    fugitiveEmis = pd.read_csv(
        config.as_input_file(config.layer_inputs.sectoral_emissions_path)
    ).to_dict(orient="records")[0]["fugitive"]  # national total from inventory
    fugitiveEmis *= 1e9  # convert to kg
    # now read climate_trace facilities emissions for coal, oil and gas
    coalFacilities = pd.read_csv(config.as_input_file(config.layer_inputs.coal_path))
    oilGasFacilities = pd.read_csv(config.as_input_file(config.layer_inputs.oil_gas_path))
    fugitiveFacilities = pd.concat((coalFacilities, oilGasFacilities))

    # select gas and year
    fugitiveCH4 = fugitiveFacilities.loc[fugitiveFacilities["gas"] == "ch4"]
    fugitiveCH4.loc[:, "start_time"] = pd.to_datetime(fugitiveCH4["start_time"])
    targetDate = (
        config.start_date
        if config.start_date <= fugitiveCH4["start_time"].max()
        else fugitiveCH4["start_time"].max()
    )  # start date or latest date in data
    years = np.array([x.year for x in fugitiveCH4["start_time"]])
    mask = years == targetDate.year
    fugitiveYear = fugitiveCH4.loc[mask, :]
    # normalise emissions to match inventory total
    fugitiveYear.loc[:, "emissions_quantity"] *= (
        fugitiveEmis / fugitiveYear["emissions_quantity"].sum()
    )

    domain_grid = config.domain_grid()

    methane = np.zeros(domain_grid.shape)

    for _, facility in fugitiveYear.iterrows():
        cell_x, cell_y, cell_valid = domain_grid.lonlat_to_cell_index(facility["lon"], facility["lat"])

        if cell_valid:
            methane[cell_y, cell_x] += facility["emissions_quantity"]

    add_sector(
        prior_ds=prior_ds,
        sector_data=convert_to_timescale(methane, domain_grid.cell_area),
        sector_meta=sector_meta,
    )


if __name__ == "__main__":
    parse_cli_to_env()
    config = load_config_from_env()

    ds = create_output_dataset(config)
    processEmissions(config, ds)
    add_ch4_total(ds)
    write_output_dataset(config, ds)
