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
import restapi # https://github.com/Bolton-and-Menk-GIS/restapi

from openmethane_prior.lib import DataSource
from openmethane_prior.lib.data_manager.parsers import parse_geo
from openmethane_prior.lib.data_manager.source import ConfiguredDataSource
from .esri_types import map_esri_date_to_str


# WA Petroleum Wells (DMIRS-025) - REST Service (ArcGIS)
# https://catalogue.data.wa.gov.au/dataset/mineral-exploration-drillholes-open-file/resource/1c61171a-3b23-4f2b-baae-04615c5bb39e
def fetch_wa_wells(data_source: ConfiguredDataSource):
    # wa_arcgis = restapi.ArcServer(url="https://public-services.slip.wa.gov.au/public/rest/services")
    wa_arcgis_mining = restapi.MapService(
        url="https://public-services.slip.wa.gov.au/public/rest/services/SLIP_Public_Services/Industry_and_Mining/MapServer"
    )

    wells_layer = wa_arcgis_mining.layer("WA Onshore Petroleum Wells (DMIRS-025)")
    wells_features = wells_layer.query(
        fields=[
            "well_name",
            "uwi",
            "lease_no",
            "operator",
            "class",
            "status",
            "rig_release_date",
        ],
        exceed_limit=True,
    )

    df = gpd.GeoDataFrame.from_features(wells_features.features)
    df["rig_release_date"] = df["rig_release_date"].map(map_esri_date_to_str)

    with open(data_source.asset_path, "w") as asset_file:
        asset_file.write(df.to_json())
        return data_source.asset_path


# Locations of all petroleum wells in the Australian state of Western Australia
# via the Data WA Portal.
# Source: https://catalogue.data.wa.gov.au/dataset/wa-onshore-petroleum-wells-dmirs-025
wa_wells_data_source = DataSource(
    name="wa-petroleum-wells",
    file_path="WA-petroleum-wells.geojson",
    fetch=fetch_wa_wells,
    parse=parse_geo,
)
