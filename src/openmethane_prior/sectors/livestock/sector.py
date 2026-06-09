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

from openmethane_prior.data_sources.inventory import (
    inventory_data_source,
    get_sector_emissions_by_code,
)
from openmethane_prior.lib.data_manager.parsers import parse_csv
from openmethane_prior.lib import (
    DataSource,
    Grid,
    logger,
    PriorSector,
    PriorSectorConfig,
)
from openmethane_prior.lib.units import seconds_in_period

logger = logger.get_logger(__name__)

livestock_headcount_data_source = DataSource(
    name="livestock-headcount",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/lmap_selected_cols_Nasimeh_171025.csv",
    parse=parse_csv,
)

def gridded_livestock_headcounts(
    livestock_df: pd.DataFrame,
    domain_grid: Grid,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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

    logger.debug(f"Mapping livestock headcounts to domain grid")
    beef_gridded = np.zeros(domain_grid.shape)
    dairy_gridded = np.zeros(domain_grid.shape)
    sheep_gridded = np.zeros(domain_grid.shape)

    row_idx = (livestock_df["iy"], livestock_df["ix"])
    np.add.at(beef_gridded, row_idx, livestock_df["heads_mapped_mix_beef"])
    np.add.at(dairy_gridded, row_idx, livestock_df["heads_mapped_dairy"])
    np.add.at(sheep_gridded, row_idx, livestock_df["heads_mapped_mix_sheep"])

    return beef_gridded, dairy_gridded, sheep_gridded


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

    # place gridded headcounts on the grid
    beef_np, dairy_np, sheep_np = gridded_livestock_headcounts(livestock_df, domain_grid)

    # get inventory totals using animal-specific UNFCCC sectors
    emissions_inventory = sector_config.data_manager.get_asset(inventory_data_source).data
    get_emissions_params = dict(
        emissions_inventory=emissions_inventory,
        start_date=config.start_date,
        end_date=config.end_date,
    )
    beef_total_emissions = get_sector_emissions_by_code(
        category_codes=["3.A.1.b", "3.A.1.c", "3.B.1.b", "3.B.1.c"], **get_emissions_params,
    )
    dairy_total_emissions = get_sector_emissions_by_code(
        category_codes=["3.A.1.a", "3.B.1.a"], **get_emissions_params,
    )
    sheep_total_emissions = get_sector_emissions_by_code(
        category_codes=["3.A.2", "3.B.2"], **get_emissions_params,
    )
    logger.debug(f"Total emissions from beef: {beef_total_emissions / 1e6:.2f} kt, dairy: {dairy_total_emissions / 1e6:.2f} kt, sheep: {sheep_total_emissions / 1e6:.2f} kt")

    beef_total_headcount = livestock_df["heads_mapped_mix_beef"].sum()
    dairy_total_headcount = livestock_df["heads_mapped_dairy"].sum()
    sheep_total_headcount = livestock_df["heads_mapped_mix_sheep"].sum()

    # distribute the national emission totals by headcount proportion
    beef_ch4_np = beef_total_emissions * beef_np / beef_total_headcount
    dairy_ch4_np = dairy_total_emissions * dairy_np / dairy_total_headcount
    sheep_ch4_np = sheep_total_emissions * sheep_np / sheep_total_headcount

    total_ch4_np = beef_ch4_np + dairy_ch4_np + sheep_ch4_np

    # convert CH4 kg to CH4 kg/s/m2
    return total_ch4_np / domain_grid.cell_area / seconds_in_period(config.start_date, config.end_date)


sector = PriorSector(
    name="livestock",
    emission_category="anthropogenic",
    unfccc_categories=[
        "3.A.1", # Enteric Fermentation - Cattle
        "3.A.2", # Enteric Fermentation - Sheep
        "3.B.1", # Manure Management - Cattle
        "3.B.2", # Manure Management - Sheep
    ],
    cf_standard_name="domesticated_livestock",
    create_estimate=process_emissions,
)
