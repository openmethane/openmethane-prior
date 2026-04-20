#
# Copyright 2025 The Superpower Institute Ltd.
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
import json
import pandas as pd

from openmethane_prior.lib import (
    DataSource,
    ConfiguredDataSource,
    logger,
)
from openmethane_prior.data_sources.inventory.inventory import kt_to_kg
from openmethane_prior.lib.data_manager.parsers import parse_csv

logger = logger.get_logger(__name__)

unfccc_codes_data_source = DataSource(
    name="ANGA-UNFCCC-codes",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    parse=parse_csv,
)


def parse_inventory(data_source: ConfiguredDataSource) -> pd.DataFrame:
    unfccc_codes_asset = data_source.data_assets[0]
    unfccc_df: pd.DataFrame = unfccc_codes_asset.data

    with open(data_source.asset_path) as anga_file:
        anga_json = json.load(anga_file)
        anga_df = pd.DataFrame.from_records(
            anga_json["value"],
            columns=[
                "InventoryYear_ID",
                "UNFCCC_Level_1", "UNFCCC_Level_2", "UNFCCC_Level_3", "UNFCCC_Level_4",
                "Gas_Level_0",
                "Gg",
            ],
        )

    # Filter out non-CH4 emissions
    anga_df = anga_df[anga_df["Gas_Level_0"] == "CH4"]

    # Convert kt to kg
    anga_df["ch4_kg"] = kt_to_kg(anga_df["Gg"])

    # Add UNFCCC code column using cascading fallback: try all 4 levels first,
    # then progressively drop the most specific level until a match is found.
    anga_df["UNFCCC_Code"] = anga_df.apply(_find_unfccc_code, axis=1, unfccc_df=unfccc_df)

    missing = anga_df[anga_df["UNFCCC_Code"].isna()]
    if not missing.empty:
        missing_distinct = missing[["UNFCCC_Level_1", "UNFCCC_Level_2", "UNFCCC_Level_3", "UNFCCC_Level_4"]].drop_duplicates()
        logger.warning(f"Categories without UNFCCC code after all fallback attempts: {missing_distinct}")

    return anga_df


_LEVEL_COLUMNS = ["UNFCCC_Level_1", "UNFCCC_Level_2", "UNFCCC_Level_3", "UNFCCC_Level_4"]
def _find_unfccc_code(row: pd.Series, unfccc_df: pd.DataFrame) -> str | None:
    """Find the closest UNFCCC code for a single ANGA row.

    Tries to match on all 4 levels first, then progressively drops the most
    specific level, only considering unfccc_df rows where the dropped levels
    are empty (i.e. parent categories).
    """
    for n_levels in range(len(_LEVEL_COLUMNS), 0, -1):
        mask = pd.Series(True, index=unfccc_df.index)
        for col in _LEVEL_COLUMNS[:n_levels]:
            mask &= unfccc_df[col] == row[col]
        for col in _LEVEL_COLUMNS[n_levels:]:
            mask &= unfccc_df[col].isna() | (unfccc_df[col] == "")
        matches = unfccc_df[mask]
        if not matches.empty:
            if n_levels < len(_LEVEL_COLUMNS):
                logger.debug(f"Used {n_levels}-level match for {[row[c] for c in _LEVEL_COLUMNS]}")
            return matches.iloc[0]["UNFCCC_Code"]
    return None

inventory_data_source = DataSource(
    name="ANGA-UNFCCC-inventory",
    url="https://greenhouseaccounts.climatechange.gov.au/OData/AR5_ParisInventory_AUSTRALIA",
    data_sources=[unfccc_codes_data_source],
    parse=parse_inventory,
)

