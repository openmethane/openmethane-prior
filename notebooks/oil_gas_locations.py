import geopandas as gpd
import os
import pathlib
from openmethane_prior.lib import PriorConfig
from openmethane_prior.lib.data_manager.manager import DataManager
from openmethane_prior.sectors.oil_gas.emission_sources.all_sources import all_emission_sources
os.environ["DOMAIN_FILE"] = "https://openmethane.s3.amazonaws.com/domains/aust10km/v1/domain.aust10km.nc"
os.environ["START_DATE"] = "2022-12-01"
os.environ["END_DATE"] = "2022-12-01"
os.environ["INPUTS"] = "../data/inputs"
os.environ["INPUT_CACHE"] = "../data/.cache"
prior_config = PriorConfig.from_env()
prior_config.prepare_paths()
prior_config.load_cached_inputs()
data_manager = DataManager(
    data_path=pathlib.Path("../data/inputs"),
    prior_config=prior_config,
)

emission_sources_df = all_emission_sources(
    data_manager=data_manager,
    prior_config=prior_config,
)

au_shp = gpd.GeoDataFrame.from_file("~/Downloads/STE_2021_AUST_SHP_GDA2020/STE_2021_AUST_GDA2020.shx").to_crs("EPSG:4326")
au_map = au_shp.plot(color='white', edgecolor='#CCCCCC', figsize=(32,24))
region_extents = {
    "QLD": (137, 155, -30, -20),
    "VIC": (146, 150, -41, -36),
    "WA": (110, 130, -35, -10),
}
region = "QLD" # set to "QLD", "VIC" or "WA" to render a sub-region
if region is not None:
    au_map.set_xlim(region_extents[region][0], region_extents[region][1])
    au_map.set_ylim(region_extents[region][2], region_extents[region][3])
emission_sources_df.to_crs("EPSG:4326").plot(ax=au_map, markersize=3, column="site_type", legend=True)
au_map


