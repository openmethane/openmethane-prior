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
import datetime
import pandas as pd

from openmethane_prior.data_sources.climate_trace import climate_trace_data_source
from openmethane_prior.lib import (
    ConfiguredDataSource,
    DataSource,
    logger,
)

logger = logger.get_logger(__name__)


def parse_coal_facilities_csv(data_source: ConfiguredDataSource) -> pd.DataFrame:
    coal_facilities_df = pd.read_csv(
        data_source.asset_path,
        converters={
            "start_time": datetime.datetime.fromisoformat,
            "end_time": datetime.datetime.fromisoformat,
        },
    )

    return coal_facilities_df

coal_facilities_data_source = DataSource(
    name="coal-facilities",
    data_sources=[climate_trace_data_source],
    parse=parse_coal_facilities_csv,
    file_path='climate-trace-AUS/DATA/fossil_fuel_operations/coal-mining_emissions_sources_v4_8_0.csv',
)
