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

from openmethane_prior.data_sources.safeguard import (
    filter_facilities,
    filter_locations,
    get_safeguard_facility_locations,
)
from openmethane_prior.lib import (
    convert_to_timescale,
    DataAsset,
    Grid,
    logger,
    polygon_cell_intersection,
    PriorConfig,
)

logger = logger.get_logger(__name__)

def allocate_safeguard_facility_emissions(
    config: PriorConfig,
    anzsic_codes: list[str],
    safeguard_facilities_asset: DataAsset,
    facility_locations_asset: DataAsset,
    reference_data_asset: DataAsset,
    grid: Grid = None,
):
    if grid is None:
        grid = config.domain_grid()

    sector_facilities = filter_facilities(
        facility_df=safeguard_facilities_asset.data,
        anzsic_codes=anzsic_codes,
        period=(config.start_date.date(), config.end_date.date()),
    )

    oil_gas_facilities, oil_gas_locations_pivot = get_safeguard_facility_locations(
        safeguard_facilities_df=sector_facilities,
        locations_df=facility_locations_asset.data,
        data_source_name=reference_data_asset.name,
    )

    oil_gas_locations = reference_data_asset.data
    oil_gas_facilities_locations = oil_gas_locations.merge(
        oil_gas_locations_pivot,
        right_on="data_source_id",
        left_on="id",
    )

    # make an empty grid to allocate emissions to
    gridded_annual_emissions = np.zeros(grid.shape)

    for _, facility in oil_gas_facilities.iterrows():
        facility_locations = filter_locations(oil_gas_facilities_locations, facility_id=facility["facility_name"])

        # use the union of all facility location shapes, which will prevent
        # overlapping shapes from being double-counted
        facility_all_areas = facility_locations["geometry"].union_all()
        facility_cells = polygon_cell_intersection(facility_all_areas, grid)

        for cell_indexes, area_proportion in facility_cells:
            # allocate a fraction of the facility emissions to each cell
            # based on the portion of the total area in each cell
            gridded_annual_emissions[cell_indexes[1], cell_indexes[0]] += facility["ch4_kg"] * area_proportion

    gridded_emissions = convert_to_timescale(gridded_annual_emissions, grid.cell_area)

    return oil_gas_facilities, oil_gas_facilities_locations, gridded_emissions
