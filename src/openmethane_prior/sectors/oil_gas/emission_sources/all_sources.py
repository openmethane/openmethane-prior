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
import geopandas as gpd
import pandas as pd

from openmethane_prior.lib import (
    logger,
    DataManager,
    PriorConfig,
)

from .emission_source import normalise_emission_source_df
from .nsw_sources import nsw_emission_sources
from .nt_sources import nt_emission_sources
from .offshore_sources import offshore_emission_sources
from .qld_sources import qld_emission_sources
from .wa_sources import wa_emission_sources
from ..data.nopta_titles import nopta_titles_data_source
from ..data.nopta_wells import nopta_wells_data_source
from ..data.nsw_drillholes import nsw_drillholes_data_source
from ..data.nsw_titles import nsw_titles_data_source
from ..data.nt_titles import nt_titles_data_source
from ..data.nt_wells import nt_wells_data_source
from ..data.qld_boreholes import qld_boreholes_data_source
from ..data.qld_leases import qld_leases_data_source
from ..data.wa_titles import wa_titles_data_source
from ..data.wa_wells import wa_wells_data_source

logger = logger.get_logger(__name__)

def all_emission_sources(
    data_manager: DataManager,
    prior_config: PriorConfig,
) -> gpd.GeoDataFrame:
    """Assemble a single DataFrame from multiple data sources, where each row
    represents a possible location of emissions in the oil and gas sector."""
    start_date = prior_config.start_date.date()
    end_date = prior_config.end_date.date()

    nsw_drillholes_da = data_manager.get_asset(nsw_drillholes_data_source)
    nsw_titles_da = data_manager.get_asset(nsw_titles_data_source)
    nsw_df = nsw_emission_sources(
        start_date=start_date,
        end_date=end_date,
        nsw_drillholes_da=nsw_drillholes_da,
        nsw_titles_da=nsw_titles_da,
    )
    nsw_df = normalise_emission_source_df(nsw_df, prior_config.crs)
    logger.debug(f"found {len(nsw_df)} NSW sources in {len(nsw_df['group_id'].unique())} titles")

    nt_wells_da = data_manager.get_asset(nt_wells_data_source)
    nt_titles_da = data_manager.get_asset(nt_titles_data_source)
    nt_df = nt_emission_sources(
        start_date=start_date,
        end_date=end_date,
        nt_wells_da=nt_wells_da,
        nt_titles_da=nt_titles_da,
    )
    nt_df = normalise_emission_source_df(nt_df, prior_config.crs)
    logger.debug(f"found {len(nt_df)} NT sources in {len(nt_df['group_id'].unique())} titles")

    qld_boreholes_da = data_manager.get_asset(qld_boreholes_data_source)
    qld_leases_da = data_manager.get_asset(qld_leases_data_source)
    qld_df = qld_emission_sources(
        start_date=start_date,
        end_date=end_date,
        qld_boreholes_da=qld_boreholes_da,
        qld_leases_da=qld_leases_da,
    )
    qld_df = normalise_emission_source_df(qld_df, prior_config.crs)
    logger.debug(f"found {len(qld_df)} QLD sources in {len(qld_df['group_id'].unique())} titles")

    wa_wells_da = data_manager.get_asset(wa_wells_data_source)
    wa_titles_da = data_manager.get_asset(wa_titles_data_source)
    wa_df = wa_emission_sources(
        start_date=start_date,
        end_date=end_date,
        wa_wells_da=wa_wells_da,
        wa_titles_da=wa_titles_da,
    )
    wa_df = normalise_emission_source_df(wa_df, prior_config.crs)
    logger.debug(f"found {len(wa_df)} WA sources in {len(wa_df['group_id'].unique())} titles")

    states_df: gpd.GeoDataFrame = pd.concat([
        nsw_df,
        nt_df,
        qld_df,
        wa_df,
    ])

    offshore_wells_da = data_manager.get_asset(nopta_wells_data_source)
    offshore_titles_da = data_manager.get_asset(nopta_titles_data_source)
    offshore_df = offshore_emission_sources(
        start_date=start_date,
        end_date=end_date,
        offshore_wells_da=offshore_wells_da,
        offshore_titles_da=offshore_titles_da,
    )
    offshore_df = normalise_emission_source_df(offshore_df, prior_config.crs)

    # NOPTA will have some wells that are already provided by state datasets,
    # which we must avoid "double counting"
    offshore_existing = states_df.sjoin_nearest(offshore_df, how="inner", max_distance=50)
    offshore_new = offshore_df[~offshore_df["data_source_id"].isin(offshore_existing["data_source_id_right"])]
    logger.debug(f"found {len(offshore_new)} offshore sources in {len(offshore_new['group_id'].unique())} titles")

    all_df: gpd.GeoDataFrame = pd.concat([
        states_df,
        offshore_new,
    ])

    return all_df

