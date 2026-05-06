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
import pandas as pd
import xarray as xr

from openmethane_prior.lib import (
    DataSource,
    convert_to_timescale,
    logger,
    PriorSector,
    PriorSectorConfig,
)
from openmethane_prior.lib.data_manager.parsers import parse_csv

logger = logger.get_logger(__name__)

livestock_headcount_data_source = DataSource(
    name="livestock-headcount",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/lmap_selected_cols_Nasimeh_171025.csv",
    parse=parse_csv,
)


def livestock_to_ch4_kg_year(beef: float, sheep: float, dairy: float) -> float:
    """Calculate the annual emissions created by a number of beef cattle, dairy
    cattle and/or sheep."""
    # TODO: document where these emission factors come from
    return beef * 51.0 + sheep * 6.8 + dairy * 93.0


def process_emissions(
    sector: PriorSector,
    sector_config: PriorSectorConfig,
    prior_ds: xr.Dataset,
):
    config = sector_config.prior_config
    domain_grid = config.domain().grid

    livestock_headcount_da = sector_config.data_manager.get_asset(livestock_headcount_data_source)
    livestock_df: pd.DataFrame = livestock_headcount_da.data
    livestock_df = livestock_df.rename(columns={"X": "lon", "Y": "lat"})

    # find the domain grid cell (ix, iy) each livestock area centre point is in
    livestock_df["ix"], livestock_df["iy"], valid_cells = domain_grid.lonlat_to_cell_index(
        lon=livestock_df["lon"],
        lat=livestock_df["lat"],
    )

    # throw away any data outside the domain
    livestock_df = livestock_df[valid_cells]

    ch4_gridded = np.zeros(domain_grid.shape)
    for _, livestock_area in livestock_df.iterrows():
        # calculate the total annual CH4 emissions for this area
        livestock_ch4 = livestock_to_ch4_kg_year(
            beef=livestock_area["heads_mapped_mix_beef"],
            sheep=livestock_area["heads_mapped_mix_sheep"],
            dairy=livestock_area["heads_mapped_dairy"],
        )
        # add the CH4 to the grid
        ch4_gridded[livestock_area["iy"], livestock_area["ix"]] += livestock_ch4

    # convert annual CH4 kg to CH4 kg/s/m3
    return convert_to_timescale(ch4_gridded, domain_grid.cell_area)


sector = PriorSector(
    name="livestock",
    emission_category="anthropogenic",
    unfccc_categories=["3.A"], # Enteric Fermentation
    cf_standard_name="domesticated_livestock",
    create_estimate=process_emissions,
)
