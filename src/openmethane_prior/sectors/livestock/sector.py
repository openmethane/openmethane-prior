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
import pyproj
import xarray as xr

from openmethane_prior.lib import (
    DataSource,
    Grid,
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

# Estimated kg CH4 emitted per animal, per year
# TODO: these figures came from example code, a reference should be added
# citing their origin
ENTERIC_ANNUAL_KG_CH4 = {
    "beef_cattle": 51.0,
    "dairy_cattle": 93.0,
    "sheep": 6.8,
}

def gridded_livestock_emissions_by_headcount(
    livestock_df: pd.DataFrame,
    domain_grid: Grid,
) -> np.ndarray:
    """Given a list of coordinates for livestock areas with headcounts of beef
    cattle, dairy cattle and sheep, calculate the annual methane emissions in
    each area, and return as gridded emissions over the domain of interest."""
    # find the domain grid cell (ix, iy) each livestock area centre point is in
    livestock_df["ix"], livestock_df["iy"], valid_cells = domain_grid.lonlat_to_cell_index(
        lon=livestock_df["lon"],
        lat=livestock_df["lat"],
    )

    # discard data outside the domain
    livestock_df = livestock_df[valid_cells]

    logger.debug(f"Calculating annual livestock emissions per headcount")
    total_ch4 = (
        livestock_df["heads_mapped_mix_beef"] * ENTERIC_ANNUAL_KG_CH4["beef_cattle"]
        + livestock_df["heads_mapped_mix_sheep"] * ENTERIC_ANNUAL_KG_CH4["sheep"]
        + livestock_df["heads_mapped_dairy"] * ENTERIC_ANNUAL_KG_CH4["dairy_cattle"]
    )

    logger.debug(f"Adding livestock emissions to domain grid")
    ch4_gridded = np.zeros(domain_grid.shape)
    np.add.at(ch4_gridded, (livestock_df["iy"], livestock_df["ix"]), total_ch4)

    return ch4_gridded


def process_emissions(
    sector: PriorSector,
    sector_config: PriorSectorConfig,
    prior_ds: xr.Dataset,
):
    config = sector_config.prior_config
    domain_grid = config.domain().grid

    livestock_headcount_da = sector_config.data_manager.get_asset(livestock_headcount_data_source)
    livestock_df: pd.DataFrame = livestock_headcount_da.data

    # dataset X/Y coords are ESPF:4283 (GDA94), convert to EPSG:4326
    transformer = pyproj.Transformer.from_crs(4283,4326)
    livestock_df["lon"], livestock_df["lat"] = transformer.transform(
        yy=livestock_df["Y"], xx=livestock_df["X"],
    )

    ch4_gridded = gridded_livestock_emissions_by_headcount(livestock_df, domain_grid)

    # convert annual CH4 kg to CH4 kg/s/m3
    return convert_to_timescale(ch4_gridded, domain_grid.cell_area)


sector = PriorSector(
    name="livestock",
    emission_category="anthropogenic",
    unfccc_categories=["3.A"], # Enteric Fermentation
    cf_standard_name="domesticated_livestock",
    create_estimate=process_emissions,
)
