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

from openmethane_prior.data_sources.climate_trace import climate_trace_data_source, parse_emissions_sources
from openmethane_prior.lib import DataSource, logger

logger = logger.get_logger(__name__)


ct_wastewaster_domestic_data_source = DataSource(
    name="ct-wastewater-domestic",
    data_sources=[climate_trace_data_source],
    parse=parse_emissions_sources,
    file_path='climate-trace-AUS/DATA/waste/domestic-wastewater-treatment-and-discharge_emissions_sources_v4_8_0.csv',
)

ct_wastewaster_industrial_data_source = DataSource(
    name="ct-wastewater-industrial",
    data_sources=[climate_trace_data_source],
    parse=parse_emissions_sources,
    file_path='climate-trace-AUS/DATA/waste/industrial-wastewater-treatment-and-discharge_emissions_sources_v4_8_0.csv',
)

ct_solid_waste_data_source = DataSource(
    name="ct-solid-waste",
    data_sources=[climate_trace_data_source],
    parse=parse_emissions_sources,
    file_path='climate-trace-AUS/DATA/waste/solid-waste-disposal_emissions_sources_v4_8_0.csv',
)