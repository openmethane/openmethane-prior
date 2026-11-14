#
# Copyright 2026 The Superpower Institute Ltd.
#
# This file is part of Open Methane.
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
from collections.abc import Callable

import geopandas as gpd
import numpy as np
import shapely
from shapely.geometry import MultiPolygon, Polygon

from openmethane_prior.lib import (
    ConfiguredDataSource,
    DataSource,
    logger,
)
from openmethane_prior.lib.data_manager.fetchers import fetch_zipped_shp_to_gdf
from openmethane_prior.lib.data_manager.parsers import parse_geo
from openmethane_prior.lib.grid.geometry import grid_mask_from_polygon_overlap
from openmethane_prior.lib.grid.grid import Grid

logger = logger.get_logger(__name__)

# Australian Maritime Boundaries 2020 (AMB2020), published by Geoscience
# Australia under CC BY 4.0. Each zip holds the Shapefile version of one
# AMB2020 theme.
# Source: https://pid.geoscience.gov.au/dataset/ga/144571
AMB2020_SSLA_URL = "https://d28rz98at9flks.cloudfront.net/144571/144571_01_0.zip"
# Source: https://pid.geoscience.gov.au/dataset/ga/144572
AMB2020_OPGGSA_URL = "https://d28rz98at9flks.cloudfront.net/144572/144572_01_0.zip"


def fetch_amb2020_areas(shp_file: str) -> Callable[[ConfiguredDataSource], pathlib.Path]:
    """Create a fetch function which stores one AMB2020 Shapefile layer as a
    GeoPackage."""
    def fetch(data_source: ConfiguredDataSource) -> pathlib.Path:
        gdf = fetch_zipped_shp_to_gdf(data_source.url, shp_file)
        gdf = gdf.rename(columns={
            "NAME": "name",
            "OBJNAM": "object_name",
            "COMMENT": "comment",
            "LEGSOU": "legal_source",
        })
        gdf = gdf[["name", "object_name", "comment", "legal_source", "geometry"]]
        gdf.to_file(data_source.asset_path, driver="GPKG")
        return data_source.asset_path

    return fetch


# Territorial sea, extending 12 nautical miles seaward from the territorial sea
# baseline. Areas landward of the baseline (land and internal waters) are not
# included in these polygons.
amb2020_territorial_sea_data_source = DataSource(
    name="AMB2020-territorial-sea",
    url=AMB2020_SSLA_URL,
    file_path="AMB2020-territorial-sea.gpkg",
    fetch=fetch_amb2020_areas("Shapefiles/Territorial_Sea_AMB2020_Areas.shp"),
    parse=parse_geo,
)

# Offshore areas under the Offshore Petroleum and Greenhouse Gas Storage Act,
# where the Commonwealth grants offshore petroleum titles. These follow the
# continental shelf and seabed treaty boundaries, which in the Timor Sea lie
# further north than the EEZ.
amb2020_offshore_areas_data_source = DataSource(
    name="AMB2020-offshore-areas",
    url=AMB2020_OPGGSA_URL,
    file_path="AMB2020-offshore-areas.gpkg",
    fetch=fetch_amb2020_areas("Shapefiles/Offshore_Areas_AMB2020_Areas.shp"),
    parse=parse_geo,
)


def au_jurisdiction_geometry(
    states: gpd.GeoDataFrame,
    territorial_sea: gpd.GeoDataFrame,
    offshore_areas: gpd.GeoDataFrame,
) -> MultiPolygon | Polygon:
    """Combine land and maritime areas into the jurisdiction of the national
    inventory.

    The result covers land, internal waters, territorial sea and offshore
    petroleum areas: the area where Australia's national inventory can report
    emissions.

    Territorial sea polygons extend seaward from the territorial sea baseline,
    leaving land and internal waters (bays, gulfs and waters inside straight
    baselines) as holes. Each polygon is replaced by its exterior ring, which
    fills those holes with everything landward of the 12 nautical mile limit.

    All inputs must share the same coordinate system.

    :param states: State and territory land boundaries
    :param territorial_sea: AMB2020 territorial sea areas
    :param offshore_areas: AMB2020 offshore areas under the Offshore Petroleum
        and Greenhouse Gas Storage Act
    :return: Shape covering the Australian jurisdiction
    """
    territorial_sea_parts = territorial_sea.geometry.make_valid().explode(index_parts=False)
    territorial_sea_parts = territorial_sea_parts[territorial_sea_parts.geom_type == "Polygon"]
    within_territorial_sea_limit = [Polygon(part.exterior) for part in territorial_sea_parts]

    return shapely.union_all([
        *states.geometry.make_valid().values,
        *within_territorial_sea_limit,
        *offshore_areas.geometry.make_valid().values,
    ])


def create_inventory_political_mask(
    grid: Grid,
    states: gpd.GeoDataFrame,
    territorial_sea: gpd.GeoDataFrame,
    offshore_areas: gpd.GeoDataFrame,
) -> np.ndarray:
    """Create a 0/1 mask of grid cells which share any area with Australia's
    jurisdiction.

    The jurisdiction is built by au_jurisdiction_geometry. Any overlap is
    enough, rather than a majority of the cell, so that every emission source
    inside the jurisdiction falls in a masked cell, including offshore
    facilities in cells which straddle an international boundary.

    All inputs must be in the grid's coordinate system.

    :return: Gridded int8 values, 1 inside the jurisdiction and 0 outside
    """
    jurisdiction = au_jurisdiction_geometry(
        states=states,
        territorial_sea=territorial_sea,
        offshore_areas=offshore_areas,
    )
    return grid_mask_from_polygon_overlap(grid, jurisdiction).astype(np.int8)
