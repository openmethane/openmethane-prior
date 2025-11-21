#
# Copyright 2025 The Superpower Institute Ltd.
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
from owslib.wfs import WebFeatureService

from openmethane_prior.lib import DataSource
from openmethane_prior.lib.data_manager.parsers import parse_geo
from openmethane_prior.lib.data_manager.source import ConfiguredDataSource


def fetch_oil_gas(data_source: ConfiguredDataSource):
    geoserver_wfs = WebFeatureService("https://opendata.maps.vic.gov.au/geoserver/wfs", version="2.0.0")

    oil_gas_feature = geoserver_wfs.getfeature(
        typename="open-data-platform:oilgas",
        srsname="urn:ogc:def:crs:EPSG::4326",
        outputFormat="application/json",
    )

    with open(data_source.asset_path, "wb") as asset_file:
        asset_file.write(bytes(oil_gas_feature.read()))
        return data_source.asset_path


# Locations and shapes of oil and gas fields in the Australian state of
# Victoria, via the Victorian Open Data provider.
# Source: https://discover.data.vic.gov.au/dataset/oil-and-gas-fields
vic_oil_gas_data_source = DataSource(
    name="vic-oil-gas-fields",
    file_path="VIC-oilgas.geojson",
    fetch=fetch_oil_gas,
    parse=parse_geo,
)
