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
import datetime
import geopandas as gpd
import pandas as pd

from openmethane_prior.lib.data_manager.manager import DataManager
from openmethane_prior.sectors.oil_gas.data.nsw_drillholes import nsw_drillholes_data_source
from openmethane_prior.sectors.oil_gas.data.nsw_titles import nsw_titles_data_source

from .nsw_sources import nsw_emission_sources
from .offshore_sources import offshore_emission_sources
from .qld_sources import qld_emission_sources
from .wa_sources import wa_emission_sources
from ..data.nopta_titles import nopta_titles_data_source
from ..data.nopta_wells import nopta_wells_data_source
from ..data.qld_boreholes import qld_boreholes_data_source
from ..data.qld_leases import qld_leases_data_source
from ..data.wa_titles import wa_titles_data_source
from ..data.wa_wells import wa_wells_data_source


def all_emission_sources(
    data_manager: DataManager,
    start_date: datetime.date,
    end_date: datetime.date,
) -> gpd.GeoDataFrame:
    """Assemble a single DataFrame from multiple data sources, where each row
    represents a possible location of emissions in the oil and gas sector."""
    nsw_drillholes_da = data_manager.get_asset(nsw_drillholes_data_source)
    nsw_titles_da = data_manager.get_asset(nsw_titles_data_source)
    nsw_df = nsw_emission_sources(
        start_date=start_date,
        end_date=end_date,
        nsw_drillholes_da=nsw_drillholes_da,
        nsw_titles_da=nsw_titles_da,
    )

    qld_boreholes_da = data_manager.get_asset(qld_boreholes_data_source)
    qld_leases_da = data_manager.get_asset(qld_leases_data_source)
    qld_df = qld_emission_sources(
        start_date=start_date,
        end_date=end_date,
        qld_boreholes_da=qld_boreholes_da,
        qld_leases_da=qld_leases_da,
    )

    wa_wells_da = data_manager.get_asset(wa_wells_data_source)
    wa_titles_da = data_manager.get_asset(wa_titles_data_source)
    wa_df = wa_emission_sources(
        start_date=start_date,
        end_date=end_date,
        wa_wells_da=wa_wells_da,
        wa_titles_da=wa_titles_da,
    )

    offshore_wells_da = data_manager.get_asset(nopta_wells_data_source)
    offshore_titles_da = data_manager.get_asset(nopta_titles_data_source)
    offshore_df = offshore_emission_sources(
        start_date=start_date,
        end_date=end_date,
        offshore_wells_da=offshore_wells_da,
        offshore_titles_da=offshore_titles_da,
    )

    all_df: gpd.GeoDataFrame = pd.concat([
        nsw_df,
        qld_df,
        wa_df,
        offshore_df,
    ])

    return all_df

