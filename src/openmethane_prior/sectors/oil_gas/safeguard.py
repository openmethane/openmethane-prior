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
import datetime
import geopandas as gpd
import numpy as np
import pandas as pd

from openmethane_prior.data_sources.safeguard import filter_facilities
from openmethane_prior.lib.grid.geometry import grid_mask_from_polygon
from openmethane_prior.lib.grid.grid import Grid
from openmethane_prior.lib.logger import get_logger
from openmethane_prior.lib.units import days_in_period

logger = get_logger(__name__)

def get_sector_safeguard_facilities(
    safeguard_facilities_df: pd.DataFrame,
    anzsic_codes: list[str] = None,
    period: tuple[datetime.date, datetime.date] = None,
):
    """Find Safeguard Mechanism facilities in the provided sector with reported
    emissions in the period of interest. Scale the annual Safeguard emissions
    to the length of the period.

    :return: DataFrame of facilities with the total CH4 emissions expected
      over the period.
    """
    # identify Safeguard Mechanism facilities in this sector which reported
    # emissions during the period of interest
    sector_facilities_df = filter_facilities(
        facility_df=safeguard_facilities_df,
        anzsic_codes=anzsic_codes,
        period=period,
    )

    if len(sector_facilities_df) == 0:
        logger.info(f"No Safeguard facilities found for the period")
        return sector_facilities_df

    logger.info(f"Found {len(sector_facilities_df)} Safeguard facilities, totalling {sector_facilities_df['ch4_kg'].sum() / 1e6:.2f} kt annual CH4")

    # scale annual safeguard emissions to the total amount for the period (kg),
    # the same unit output from get_sector_emissions_by_code
    safeguard_period_start = sector_facilities_df.iloc[0]["reporting_start"]
    safeguard_period_end = sector_facilities_df.iloc[0]["reporting_end"]
    year_days = days_in_period(safeguard_period_start, safeguard_period_end)
    period_days = days_in_period(period[0], period[1])
    sector_facilities_df["ch4_kg"] *= period_days / year_days

    logger.info(f"{sector_facilities_df['ch4_kg'].sum() / 1e6:.2f} kt total Safeguard emissions in the period in sectors: {','.join(anzsic_codes)}")

    return sector_facilities_df


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
