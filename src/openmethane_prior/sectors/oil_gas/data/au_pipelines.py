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

from openmethane_prior.lib import ConfiguredDataSource, DataSource
from openmethane_prior.lib.data_manager.parsers import parse_geo


def fetch_au_gas_pipelines(data_source: ConfiguredDataSource):
    au_spatial_pipelines = restapi.MapService(
        url="https://services.ga.gov.au/gis/rest/services/Oil_Gas_Pipelines/MapServer"
    )

    # GA data source includes two layers: "Oil_Pipelines", "Gas_Pipelines"
    # However, methane emissions from oil pipelines seems unlikely.
    pipelines_layer = au_spatial_pipelines.layer("Gas_Pipelines")
    pipelines_features = pipelines_layer.query(
        fields=[
            'objectid',
            'feature_type',
            'name',
            'length',
            'state',
            'operational_status',
            'source',
            'license',
        ],
        exceed_limit=True,
    )
    df = gpd.GeoDataFrame.from_features(pipelines_features.features)

    with open(data_source.asset_path, "w") as asset_file:
        asset_file.write(df.to_json())
        return data_source.asset_path


# Locations of gas pipelines in Australia, via Geoscience Australia.
# Source: https://ecat.ga.gov.au/geonetwork/srv/eng/catalog.search#/metadata/147583
au_gas_pipelines_data_source = DataSource(
    name="AU-gas-pipelines",
    file_path="AU-gas-pipelines.geojson",
    fetch=fetch_au_gas_pipelines,
    parse=parse_geo,
)
