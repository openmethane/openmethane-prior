import datetime
import geopandas as gpd
import os
import pandas as pd
import pathlib
from openmethane_prior.lib import PriorConfig
from openmethane_prior.lib.data_manager.manager import DataManager
from openmethane_prior.sectors.oil_gas.data.nsw_drillholes import nsw_drillholes_data_source
from openmethane_prior.sectors.oil_gas.data.nsw_titles import nsw_titles_data_source
from openmethane_prior.sectors.oil_gas.data.qld_boreholes import qld_boreholes_data_source
from openmethane_prior.sectors.oil_gas.data.qld_leases import qld_leases_data_source
from openmethane_prior.sectors.oil_gas.data.wa_titles import wa_titles_data_source
from openmethane_prior.sectors.oil_gas.data.wa_wells import wa_wells_data_source
from openmethane_prior.sectors.oil_gas.emission_sources.nsw_sources import nsw_emission_sources
from openmethane_prior.sectors.oil_gas.emission_sources.qld_sources import qld_emission_sources
from openmethane_prior.sectors.oil_gas.emission_sources.wa_sources import wa_emission_sources
os.environ["START_DATE"] = "2023-07-01"
os.environ["END_DATE"] = "2023-07-01"
prior_config = PriorConfig.from_env()
data_manager = DataManager(
    data_path=pathlib.Path("../data/inputs"),
    prior_config=prior_config,
)

nsw_drillholes_da = data_manager.get_asset(nsw_drillholes_data_source)
nsw_titles_da = data_manager.get_asset(nsw_titles_data_source)
nsw_df = nsw_emission_sources(
    start_date=datetime.date(2021, 1, 1),
    end_date=datetime.date(2023, 1, 2),
    nsw_drillholes_da=nsw_drillholes_da,
    nsw_titles_da=nsw_titles_da,
)
qld_boreholes_da = data_manager.get_asset(qld_boreholes_data_source)
qld_leases_da = data_manager.get_asset(qld_leases_data_source)
qld_df = qld_emission_sources(
    start_date=datetime.date(2021, 1, 1),
    end_date=datetime.date(2023, 1, 2),
    qld_boreholes_da=qld_boreholes_da,
    qld_leases_da=qld_leases_da,
)
wa_wells_da = data_manager.get_asset(wa_wells_data_source)
wa_titles_da = data_manager.get_asset(wa_titles_data_source)
wa_df = wa_emission_sources(
    start_date=datetime.date(2021, 1, 1),
    end_date=datetime.date(2023, 1, 2),
    wa_wells_da=wa_wells_da,
    wa_titles_da=wa_titles_da,
)
all_df = pd.concat([nsw_df, qld_df, wa_df])

au_shp = gpd.GeoDataFrame.from_file("~/Downloads/STE_2021_AUST_SHP_GDA2020/STE_2021_AUST_GDA2020.shx")
au_map = au_shp.plot(color='white', edgecolor='#CCCCCC', figsize=(32,24))
nsw_titles_da.data.plot(ax=au_map, alpha=0.5)
qld_leases_da.data.plot(ax=au_map, alpha=0.5)
# wa_wells_da.data.plot(ax=au_map, markersize=3, column="class", legend=True)
wa_titles_da.data.plot(ax=au_map, alpha=0.5)
all_df.plot(ax=au_map, markersize=3, column="site_type", legend=True)
au_map


