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
import csv
import json
import pandas as pd

from openmethane_prior.lib import DataSource, ConfiguredDataSource
from openmethane_prior.data_sources.inventory.inventory import SectorEmission, create_emissions_inventory
from openmethane_prior.data_sources.inventory.unfccc import create_category_list, Category

def parse_category_csv(data_source: ConfiguredDataSource) -> list[Category]:
    with open(data_source.asset_path, newline='') as codes_file:
        reader = csv.reader(codes_file)
        next(reader) # skip header row
        return create_category_list(categories=reader)

unfccc_codes_data_source = DataSource(
    name="ANGA-UNFCCC-codes",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/UNFCCC-codes-AU.csv",
    parse=parse_category_csv,
)


def parse_inventory(data_source: ConfiguredDataSource) -> list[SectorEmission]:
    unfccc_codes_asset = data_source.data_assets[0]

    with open(data_source.asset_path) as anga_file:
        anga_json = json.load(anga_file)
        anga_df = pd.DataFrame.from_records(anga_json["value"])

    # Filter out non-CH4 emissions
    anga_df = anga_df[anga_df["Gas_Level_0"] == "CH4"]

    rows = []
    for index, values in anga_df.iterrows():
        rows.append([
            values["InventoryYear_ID"],
            values["UNFCCC_Level_1"],
            values["UNFCCC_Level_2"],
            values["UNFCCC_Level_3"],
            values["UNFCCC_Level_4"],
            values["UNFCCC_Level_5"],
            values["Gg"],
        ])

    return create_emissions_inventory(categories=unfccc_codes_asset.data, inventory_list=rows)

inventory_data_source = DataSource(
    name="ANGA-UNFCCC-inventory",
    url="https://greenhouseaccounts.climatechange.gov.au/OData/AR5_ParisInventory_AUSTRALIA",
    data_sources=[unfccc_codes_data_source],
    parse=parse_inventory,
)

