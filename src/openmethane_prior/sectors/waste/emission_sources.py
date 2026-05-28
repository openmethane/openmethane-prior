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
import numpy as np
import pandas as pd

from openmethane_prior.data_sources.climate_trace import filter_emissions_sources
from openmethane_prior.lib import (
    DataManager,
    PriorConfig,
)

from .data import (
    ct_wastewaster_domestic_data_source,
    ct_wastewaster_industrial_data_source,
    ct_solid_waste_data_source,
)

def waste_emission_sources(config: PriorConfig, data_manager: DataManager):
    # read all emissions sources corresponding to the waste sector
    wastewater_domestic_df = data_manager.get_asset(ct_wastewaster_domestic_data_source).data
    wastewater_industrial_df = data_manager.get_asset(ct_wastewaster_industrial_data_source).data
    solid_waste_df = data_manager.get_asset(ct_solid_waste_data_source).data

    emission_sources_df = pd.concat([
        wastewater_domestic_df,
        wastewater_industrial_df,
        solid_waste_df,
    ])

    # ClimateTRACE has "emission_quantity" column with their own estimate.
    # Add a column for the emission from each source from inventories, using
    # NaN to indicate "not yet allocated" instead of "no emission"
    emission_sources_df["inventory_quantity"] = np.nan

    # select the emissions source data from the requested period
    emission_sources_df = filter_emissions_sources(
        emissions_sources_df=emission_sources_df,
        period_start=config.start_date,
        period_end=config.end_date,
    )

    return emission_sources_df