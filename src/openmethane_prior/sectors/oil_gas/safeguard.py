#
# Copyright 2023 The Superpower Institute Ltd.
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
import geopandas as gpd
import numpy as np
import pandas as pd

from openmethane_prior.lib.grid.geometry import grid_mask_from_polygon
from openmethane_prior.lib.grid.grid import Grid
from openmethane_prior.lib.logger import get_logger

logger = get_logger(__name__)


def gas_supply_emissions(
    domain_grid: Grid,
    facilities_df: pd.DataFrame,
    au_states: gpd.GeoDataFrame,
    nightlights: np.ndarray[tuple[int, int], np.dtype[np.float64]]
) -> np.ndarray[tuple[int, int], np.dtype[np.float64]]:
    """Allocates emissions from gas supply networks based on nighttime lights
    in their state. This function aggregates emissions from all facilities in
    each state, since we lack specific polygon extents of individual networks.

    :param domain_grid: Grid representing the Domain
    :param facilities_df: List of facilities with a state and emission quantity
    :param au_states: GeoDataFrame with the shape of each state
    :param nightlights: Night lights gridded to the domain of interest
    :return: Emissions from facilities gridded to the domain of interest
    """
    gridded_emission = np.zeros(domain_grid.shape)

    logger.debug(f"Found {len(facilities_df)} gas supply facilities totalling {facilities_df['ch4_kg'].sum() / 1e6:.2f} kt CH4 in the period")
    for state in facilities_df["state"].unique():
        # combine all gas supply facility emissions in the state
        state_facilities = facilities_df[facilities_df["state"] == state]
        total_emission = state_facilities["ch4_kg"].sum()

        state_shape = au_states[au_states["short_name"] == state]
        if len(state_shape) != 1:
            pass

        # mask the nightlights to only the state, and rescale their values
        # so each cell value is its proportion of the whole
        state_geometry = state_shape.iloc[0]["geometry"]
        state_mask = grid_mask_from_polygon(domain_grid, state_geometry)
        if state_mask.sum() == 0:
            # no overlap between the state and the domain
            continue
        state_nightlights = nightlights * state_mask
        state_nightlights /= state_nightlights.sum()

        # distribute the state emission to grid cells based on night lights
        gridded_emission += total_emission * state_nightlights

    return gridded_emission


def safeguard_operating_periods(
    facility_locations_df: pd.DataFrame,
    oil_gas_sites_df: pd.DataFrame,
    sites_data_source_name: str,
) -> pd.DataFrame:
    """Determine the period each Safeguard facility was in operation, based on
    the operation dates of its sites in the oil and gas sites dataset.

    A facility's location can refer to a single site by its "Site" name, or
    to all sites in a group by its "Facility name". A facility is in operation
    while any of its sites are, so the period runs from the earliest site start
    to the latest site end. A missing date on any site leaves that side of the
    period open.

    Only the oil and gas sites dataset is used, since operation dates in other
    sources (like petroleum title dates for wells) are only rough bounds.

    :return: DataFrame with columns facility_name, operation_start and
      operation_end, with one row for each facility which has sites.
    """
    site_locations_df = facility_locations_df[facility_locations_df["data_source_name"] == sites_data_source_name]

    site_matches_df = site_locations_df.merge(oil_gas_sites_df, left_on="data_source_id", right_on="Site")
    group_matches_df = site_locations_df.merge(oil_gas_sites_df, left_on="data_source_id", right_on="Facility name")
    facility_sites_df = pd.concat([site_matches_df, group_matches_df])

    operating_periods_df = facility_sites_df.groupby("safeguard_facility_name").agg(
        operation_start=("Operation start", lambda dates: pd.NaT if dates.isna().any() else dates.min()),
        operation_end=("Operation end", lambda dates: pd.NaT if dates.isna().any() else dates.max()),
    )

    return operating_periods_df.reset_index(names="facility_name")
