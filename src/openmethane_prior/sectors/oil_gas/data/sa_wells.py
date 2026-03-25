#
# Copyright 2026 The Superpower Institute Ltd.
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
import os.path
import pandas as pd
import urllib

from openmethane_prior.lib import DataSource
from openmethane_prior.lib.data_manager.parsers import parse_geo_xlsx, parse_csv
from openmethane_prior.lib.data_manager.source import ConfiguredDataSource

# Locations of all petroleum wells in the Australian state of South Australia
# via the PEPS SA Portal.
# Source: https://peps.sa.gov.au/more/excels/ -> Well Details and Locations
sa_wells_data_source = DataSource(
    name="SA-petroleum-wells",
    file_path="SAPetroleumWells.xlsx",
    url="https://onepeps-api.azurewebsites.net/api/excel/file/Wells.xlsx",
    parse=parse_geo_xlsx("GDA20 X", "GDA20 Y", "EPSG:7844"),
)


def fetch_xlsx_as_csv(data_source: ConfiguredDataSource):
    """Fetch a source file in xlsx format, but save it to disk as csv."""
    if data_source.url is None:
        raise ValueError("DataSource must have url set to use default fetch")

    # urlretrieve will throw on non-successful fetches
    save_path, response = urllib.request.urlretrieve(url=data_source.url)

    df = pd.read_excel(save_path)
    df.to_csv(data_source.asset_path)

    # clean up the xlsx file
    os.remove(save_path)

    return data_source.asset_path

# Production amounts by month for each well in the SA PEPS wells dataset.
# Source: https://peps.sa.gov.au/more/excels/ -> Monthly Production by Completion
sa_wells_production_data_source = DataSource(
    name="SA-wells-production",
    file_path="SA-wells-production.csv",
    url="https://onepeps-api.azurewebsites.net/api/excel/file/MonthlyProductionByCompletion.xlsx",
    fetch=fetch_xlsx_as_csv,
    parse=parse_csv,
)
