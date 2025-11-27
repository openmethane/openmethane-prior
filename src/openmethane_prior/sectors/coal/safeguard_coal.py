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

import numpy as np
import pandas as pd

from openmethane_prior.data_sources.safeguard.location import get_safeguard_facility_locations
from openmethane_prior.data_sources.safeguard import (
    filter_facilities,
    filter_locations,
)
from openmethane_prior.lib.data_manager.parsers import parse_csv
from openmethane_prior.lib import (
    convert_to_timescale,
    DataAsset,
    logger,
    PriorConfig,
)

logger = logger.get_logger(__name__)

def allocate_safeguard_facility_emissions(
    config: PriorConfig,
    anzsic_codes: list[str],
    safeguard_facilities_asset: DataAsset,
    facility_locations_asset: DataAsset,
    reference_data_asset: DataAsset,
):
    domain_grid = config.domain_grid()

    sector_facilities = filter_facilities(
        facility_df=safeguard_facilities_asset.data,
        anzsic_codes=anzsic_codes,
        period=(config.start_date.date(), config.end_date.date()),
    )

    coal_facilities, coal_locations_pivot = get_safeguard_facility_locations(
        safeguard_facilities_df=sector_facilities,
        locations_df=facility_locations_asset.data,
        data_source_name=reference_data_asset.name,
    )

    # each facility in the coal dataset has multiple rows, we only need a
    # single lat/lon pair for each
    coal_locations = reference_data_asset.data[["source_name", "lat", "lon"]].drop_duplicates()
    coal_facilities_locations = pd.merge(
        coal_locations_pivot,
        coal_locations,
        left_on="data_source_id",
        right_on="source_name",
    )

    gridded_annual_emissions = np.zeros(config.domain_grid().shape)

    for _, facility in coal_facilities.iterrows():
        facility_locations = filter_locations(coal_facilities_locations, facility_id=facility["facility_name"])
        for _, location in facility_locations.iterrows():
            cell_x, cell_y, cell_valid = domain_grid.lonlat_to_cell_index(location["lon"], location["lat"])

            if cell_valid:
                # naively distribute reported emissions evenly to location
                location_emissions = facility["ch4_kg"] / len(facility_locations)
                gridded_annual_emissions[cell_y, cell_x] += location_emissions

    gridded_emissions = convert_to_timescale(gridded_annual_emissions, config.domain_grid().cell_area)

    return coal_facilities, coal_facilities_locations, gridded_emissions
