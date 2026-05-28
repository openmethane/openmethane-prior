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
import urllib.request

from openmethane_prior.lib import (
    DataSource,
    Domain,
    ConfiguredDataSource,
    logger,
)
from openmethane_prior.lib.data_manager.parsers import parse_csv

from .inventory import create_inventory_df

logger = logger.get_logger(__name__)

def rows_from_children(tree, parents = None) -> list:
    rows = []
    if tree["level"] > 5: # 5 levels is enough detail for us
        return rows

    levels = [*parents] if parents is not None else []
    if tree["level"] > 0:
        code, name = tree["name"].split(" ", 1)
        levels.append(name)
        rows.append([code, *levels])
    for child in tree["children"]:
        rows += rows_from_children(child, levels)
    return rows


def fetch_unfccc_codes(data_source: ConfiguredDataSource):
    """Fetch the heirarchy of UNFCCC codes used on the ANGA website, where
    the UNFCCC codes are displayed along with the same category names used
    in the API."""
    with urllib.request.urlopen(data_source.url) as anga_api_defaults:
        response = json.loads(anga_api_defaults.read().decode())
        unfccc_tree = response["sectortreeParis"]["Nodes"]
    unfccc_rows = rows_from_children(unfccc_tree[0])
    df = pd.DataFrame(
        data=unfccc_rows,
        columns=["UNFCCC_Code", "UNFCCC_Level_1", "UNFCCC_Level_2", "UNFCCC_Level_3", "UNFCCC_Level_4", "UNFCCC_Level_5"],
    )
    # Levels > 5 are stripped, resulting in duplicates with the same code
    df.drop_duplicates(subset=["UNFCCC_Code"], keep="first", inplace=True)
    df.to_csv(data_source.asset_path, index=False)
    return data_source.asset_path


# UNFCCC category codes with detailed level names which match the level names
# in the ANGA UNFCCC/Paris Inventory dataset. The url and fetch method use an
# **unofficial and undocumented** API used by the ANGA website to display
# the UNFCCC category hierarchy. This is necessary because the inventory
# dataset only includes level name text without UNFCCC codes, and the levels
# do not match official UNFCCC category text, and are unstable year to year.
# Source: https://www.greenhouseaccounts.climatechange.gov.au/
unfccc_codes_data_source = DataSource(
    name="ANGA-UNFCCC-codes",
    url="https://www.greenhouseaccounts.climatechange.gov.au/api/Defaults",
    file_path="ANGA-UNFCCC-codes.csv",
    fetch=fetch_unfccc_codes,
    parse=parse_csv,
)


def parse_inventory(data_source: ConfiguredDataSource) -> pd.DataFrame:
    unfccc_codes_asset = data_source.data_assets[0]
    unfccc_df: pd.DataFrame = unfccc_codes_asset.data

    with open(data_source.asset_path) as anga_file:
        anga_json = json.load(anga_file)
        return create_inventory_df(anga_json["value"], unfccc_df)

# Australia's National Greenhouse Accounts emission inventory, broken down by
# economic sector using UNFCCC sector categories.
# Source: https://www.greenhouseaccounts.climatechange.gov.au/ -> Datasets and API
inventory_data_source = DataSource(
    name="ANGA-UNFCCC-inventory",
    url="https://greenhouseaccounts.climatechange.gov.au/OData/AR5_ParisInventory_AUSTRALIA",
    data_sources=[unfccc_codes_data_source],
    parse=parse_inventory,
)


qld_inventory_data_source = DataSource(
    name="ANGA-UNFCCC-inventory-QLD",
    url="https://greenhouseaccounts.climatechange.gov.au/OData/AR5_ParisInventory_QLD",
    data_sources=[unfccc_codes_data_source],
    parse=parse_inventory,
)


def parse_domain(data_source: ConfiguredDataSource) -> Domain:
    return Domain.from_file(data_source.asset_path)


inventory_domain_data_source = DataSource(
    name="AU-inventory-domain",
    url="https://openmethane.s3.amazonaws.com/domains/aust10km/v1/domain.aust10km.nc",
    parse=parse_domain,
)