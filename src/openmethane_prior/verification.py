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

"""Utilities for verifying the generated output file"""

import numpy as np
import pandas as pd
import xarray as xr
from colorama import Fore

from openmethane_prior.config import PriorConfig, load_config_from_env
from openmethane_prior.data_manager.manager import DataManager
from openmethane_prior.inventory.data import create_inventory
from openmethane_prior.outputs import SECTOR_PREFIX
from openmethane_prior.inventory.inventory import get_sector_emissions_by_code

from openmethane_prior.layers.omIndustrialStationaryTransportEmis import sector_meta_map as ntlt_sector_meta
from openmethane_prior.layers.omAgLulucfWasteEmis import sector_meta_map as landuse_sector_meta, livestock_data_source
from openmethane_prior.layers.omElectricityEmis import sector_meta as electricity_sector_meta
from openmethane_prior.layers.omFugitiveEmis import sector_meta as fugitive_sector_meta

import openmethane_prior.logger as logger
from openmethane_prior.units import days_in_period

logger = logger.get_logger(__name__)

MAX_ABS_DIFF = 0.1


def verify_emis(config: PriorConfig, prior_ds: xr.Dataset, atol: float = MAX_ABS_DIFF):
    """Check output sector emissions to make sure they tally up to the input emissions"""
    if config.domain_grid() != config.inventory_grid():
        # TODO: is there a sense check we can do on smaller domains?
        logger.info("SKIPPING verify_emis: only supported when domain and inventory domain are identical")
        return

    data_manager = DataManager(data_path=config.input_path)
    emissions_inventory = create_inventory(data_manager=data_manager)

    inventory_sectors = [
        fugitive_sector_meta,
        electricity_sector_meta,
        *ntlt_sector_meta.values(),
        *landuse_sector_meta.values(),
    ]

    m2s_to_kg = config.domain_grid().cell_area * 24 * 60 * 60
    ds_start_date = pd.to_datetime(prior_ds['time'][0].item()).date()
    ds_end_date = pd.to_datetime(prior_ds['time'][-1].item()).date()
    period_days = days_in_period(ds_start_date, ds_end_date)

    total_expected_vs_actual = []

    # Load Livestock inventory and check prior values don't exceed data source
    if f"{SECTOR_PREFIX}_livestock" in prior_ds:
        livestock_asset = data_manager.get_asset(livestock_data_source)
        ls = xr.open_dataset(livestock_asset.path)
        livestock_inventory_total = round(np.sum(ls["CH4_total"].values)) * (period_days / 365)
        livestock_prior_total = float(prior_ds[f"{SECTOR_PREFIX}_livestock"].sum()) * m2s_to_kg
        total_expected_vs_actual.append(("livestock", livestock_inventory_total, livestock_prior_total))


    # Check each layer in the output sums up to the input
    for sector in inventory_sectors:
        ds_var_name = f"{SECTOR_PREFIX}_{sector.name}"
        inventory_total = get_sector_emissions_by_code(
            emissions_inventory=emissions_inventory,
            start_date=ds_start_date,
            end_date=ds_end_date,
            category_codes=sector.unfccc_categories,
        )

        if ds_var_name in prior_ds:
            # convert emissions in each day in kg/m2/s to kg and sum them
            prior_total = float(prior_ds[ds_var_name].sum()) * m2s_to_kg
            total_expected_vs_actual.append((sector.name, inventory_total, prior_total))

    passed = []
    failed = []
    for sector_name, expected, actual in total_expected_vs_actual:
        pct_diff = round(actual - expected) / expected * 100

        if abs(pct_diff) > atol:
            failed.append(f"Discrepancy of {pct_diff}% in {sector_name} emissions")
        else:
            passed.append(f"{sector_name} emissions OK, discrepancy is {abs(pct_diff)}% of total")

    for passed_msg in passed:
        logger.debug(f"{Fore.GREEN}PASSED{Fore.RESET} - {passed_msg}")
    for failed_msg in failed:
        logger.warning(f"{Fore.RED}FAILED{Fore.RESET} - {failed_msg}")

if __name__ == "__main__":
    config = load_config_from_env()
    verify_emis(config=config, prior_ds=xr.open_dataset(config.output_file))
