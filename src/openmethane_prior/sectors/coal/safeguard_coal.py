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

from openmethane_prior.data_sources.safeguard import get_safeguard_facility_locations
from openmethane_prior.lib import (
    Grid,
    logger,
)

logger = logger.get_logger(__name__)


def allocate_safeguard_facility_emissions(
    domain_grid: Grid,
    safeguard_facilities_df: pd.DataFrame,
    facility_locations_df: pd.DataFrame,
    coal_facilities_df: pd.DataFrame,
    coal_data_source_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    """Allocate Safeguard Mechanism coal facility emissions to coal mines.

    Each facility's emissions are divided equally between the coal mines it
    is located at.

    Parameters
    ----------
    domain_grid
        Grid to allocate emissions onto.
    safeguard_facilities_df
        Safeguard facilities in the sector, with ``ch4_kg`` already scaled to
        the period of interest, as returned by
        ``get_sector_safeguard_facilities``.
    facility_locations_df
        Safeguard facility locations, as parsed from the
        ``safeguard-locations`` data source.
    coal_facilities_df
        Coal mines with ``source_name``, ``lat`` and ``lon`` columns. Mines
        may have more than one row.
    coal_data_source_name
        Name of the data source ``coal_facilities_df`` was read from, used to
        select the matching rows of ``facility_locations_df``.

    Returns
    -------
    tuple
        - Facilities which could be located at one or more coal mines. Only
          these emissions have been allocated. Emissions of facilities which
          could not be located should remain in the sector's unallocated
          total.
        - Locations of the allocated facilities, one row per facility and mine.
        - Total emissions over the period in each grid cell (kg). Mines
          outside the domain are counted as allocated but don't appear on
          the grid.
    """
    _, coal_locations_pivot = get_safeguard_facility_locations(
        safeguard_facilities_df=safeguard_facilities_df,
        locations_df=facility_locations_df,
        data_source_name=coal_data_source_name,
    )

    # each mine in the coal dataset has multiple rows, we only need a single
    # lat/lon pair for each. a location referencing a mine which isn't in the
    # coal dataset is dropped here, so its facility is treated as unlocated.
    coal_lonlat = coal_facilities_df[["source_name", "lat", "lon"]].drop_duplicates()
    facility_locations = coal_locations_pivot.merge(
        coal_lonlat,
        left_on="data_source_id",
        right_on="source_name",
    )

    located_mask = safeguard_facilities_df["facility_name"].isin(
        facility_locations["safeguard_facility_name"]
    )
    for _, facility in safeguard_facilities_df[~located_mask].iterrows():
        logger.warning(
            f"No coal mine found for Safeguard facility '{facility['facility_name']}', "
            f"leaving {facility['ch4_kg']:.2f}kg CH4 in the unallocated sector total"
        )
    located_facilities = safeguard_facilities_df[located_mask]

    # naively distribute each facility's emissions evenly to its locations
    location_count = facility_locations.groupby("safeguard_facility_name")[
        "safeguard_facility_name"
    ].transform("size")
    facility_ch4 = facility_locations["safeguard_facility_name"].map(
        located_facilities.set_index("facility_name")["ch4_kg"]
    )
    location_ch4 = (facility_ch4 / location_count).to_numpy()

    gridded_emissions = np.zeros(domain_grid.shape)
    cell_x, cell_y, cell_valid = domain_grid.lonlat_to_cell_index(
        facility_locations["lon"].to_numpy(),
        facility_locations["lat"].to_numpy(),
    )
    np.add.at(gridded_emissions, (cell_y[cell_valid], cell_x[cell_valid]), location_ch4[cell_valid])

    return located_facilities, facility_locations, gridded_emissions
