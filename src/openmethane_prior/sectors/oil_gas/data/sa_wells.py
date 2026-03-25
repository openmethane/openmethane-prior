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
from openmethane_prior.lib import DataSource
from openmethane_prior.lib.data_manager.parsers import parse_geo_xlsx, parse_xlsx

# Locations of all petroleum wells in the Australian state of South Australia
# via the PEPS SA Portal.
# Source: https://peps.sa.gov.au/more/excels/ -> Well Details and Locations
sa_wells_data_source = DataSource(
    name="SA-petroleum-wells",
    file_path="SAPetroleumWells.xlsx",
    url="https://onepeps-api.azurewebsites.net/api/excel/file/Wells.xlsx",
    parse=parse_geo_xlsx("GDA20 X", "GDA20 Y", "EPSG:7844"),
)


# Production amounts by month for each well in the SA PEPS wells dataset.
# Source: https://peps.sa.gov.au/more/excels/ -> Monthly Production by Completion
sa_wells_production_data_source = DataSource(
    name="SA-wells-production",
    file_path="MonthlyProductionByCompletion.xlsx",
    url="https://onepeps-api.azurewebsites.net/api/excel/file/MonthlyProductionByCompletion.xlsx",
    parse=parse_xlsx,
)
