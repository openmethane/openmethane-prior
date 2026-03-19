import datetime
import geopandas as gpd
import matplotlib.pyplot as plt
import os
import pathlib
from openmethane_prior.lib import PriorConfig
from openmethane_prior.lib.data_manager.manager import DataManager
from openmethane_prior.sectors.oil_gas.data.wa_titles import wa_titles_data_source
from openmethane_prior.sectors.oil_gas.data.wa_wells import wa_wells_data_source
from openmethane_prior.sectors.oil_gas.emission_sources.wa_sources import wa_emission_sources
os.environ["START_DATE"] = "2023-07-01"
os.environ["END_DATE"] = "2023-07-01"
prior_config = PriorConfig.from_env()
data_manager = DataManager(
    data_path=pathlib.Path("../data"),
    prior_config=prior_config,
)

wa_wells_df = data_manager.get_asset(wa_wells_data_source)
wa_titles_df = data_manager.get_asset(wa_titles_data_source)
df = wa_emission_sources(
    start_date=datetime.date(2021, 1, 1),
    end_date=datetime.date(2023, 1, 2),
    wa_wells_df=wa_wells_df.data,
    wa_titles_df=wa_titles_df.data,
)
df

au_shp = gpd.GeoDataFrame.from_file("~/Downloads/STE_2021_AUST_SHP_GDA2020/STE_2021_AUST_GDA2020.shx")
au_map = au_shp.plot(color='white', edgecolor='#CCCCCC', figsize=(32,24))
wa_titles_df.data.plot(ax=au_map, alpha=0.5)
# wa_wells_df.data.plot(ax=au_map, markersize=3, column="class", legend=True)
df.plot(ax=au_map, markersize=3, column="class", legend=True)
au_map


