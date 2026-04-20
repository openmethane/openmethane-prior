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
from openmethane_prior.lib.data_manager.parsers import parse_csv

from .inventory import create_inventory_df

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
        return create_inventory_df(anga_json["value"], unfccc_df)


inventory_data_source = DataSource(
    name="ANGA-UNFCCC-inventory",
    url="https://greenhouseaccounts.climatechange.gov.au/OData/AR5_ParisInventory_AUSTRALIA",
    data_sources=[unfccc_codes_data_source],
    parse=parse_inventory,
)

