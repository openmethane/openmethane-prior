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
import pathlib

from openmethane_prior.lib.data_manager.fetchers import fetch_zipped_shp_to_gdf
from openmethane_prior.lib.data_manager.parsers import parse_geo
from openmethane_prior.lib import (
    DataSource,
    ConfiguredDataSource,
    logger,
)


logger = logger.get_logger(__name__)

state_short_names = {
    "New South Wales": "NSW",
    "Victoria": "VIC",
    "Queensland": "QLD",
    "South Australia": "SA",
    "Western Australia": "WA",
    "Tasmania": "TAS",
    "Northern Territory": "NT",
    "Australian Capital Territory": "ACT",
    "Other Territories": "OT",
}
def map_state_name_to_short_name(state_name: str) -> str | None:
    return state_short_names[state_name] if state_name in state_short_names \
        else None


def fetch_au_states(data_source: ConfiguredDataSource) -> pathlib.Path:
    """Fetch a zipped Shapefile (.shp) and convert to GeoJSON using geopandas."""
    # fetch the zipfile in data_source.url and read the included Shapefile
    gdf = fetch_zipped_shp_to_gdf(data_source.url, "STE_2021_AUST_GDA2020.shp")

    gdf = gdf.rename(columns={
        "STE_CODE21": "code",
        "STE_NAME21": "name",
        "AREASQKM21": "area_sqkm",
    })
    gdf = gdf[["code", "name", "area_sqkm", "geometry"]]
    gdf["short_name"] = gdf["name"].map(map_state_name_to_short_name)

    # write the data as geojson
    with open(data_source.asset_path, "w") as asset_file:
        asset_file.write(gdf.to_json())

    return data_source.asset_path


au_shapes_states_data_source = DataSource(
    name="AU-states",
    url="https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files/STE_2021_AUST_SHP_GDA2020.zip",
    file_path='AU-states.geojson',
    fetch=fetch_au_states,
    parse=parse_geo,
)
