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
import json
from owslib.wfs import WebFeatureService

from openmethane_prior.lib import DataSource
from openmethane_prior.lib.data_manager.parsers import parse_geo
from openmethane_prior.lib.data_manager.source import ConfiguredDataSource


def fetch_nsw_titles(data_source: ConfiguredDataSource):
    geoserver_wfs = WebFeatureService("https://public-gs.geoscience.nsw.gov.au/geoserver/wfs", version="2.0.0")

    desired_properties = [
        "tas_id",
        "title",
        "holder",
        "company",
        "grant_date",
        "expiry_date",
        "minerals",
        "resource",
        "operation",
        "geom",
    ]

    nsw_titles_feature = geoserver_wfs.getfeature(
        typename="mining-and-exploration:titles_title_granted",
        srsname="urn:ogc:def:crs:EPSG::4326",
        propertyname=desired_properties,
        outputFormat="application/json",
    )

    features_df = gpd.GeoDataFrame.from_features(json.loads(nsw_titles_feature.read()))

    # only include titles relevant to petroleum production
    features_df = features_df[features_df["resource"] == "PETROLEUM"]
    features_df = features_df[features_df["operation"] == "MINING"]

    with open(data_source.asset_path, "w") as asset_file:
        asset_file.write(features_df.to_json())
        return data_source.asset_path


# Locations of coal seam gas and petroleum production titles in the
# Australian state of New South Wales, via Geosciences NSW.
# Source: https://data.nsw.gov.au/data/dataset/nsw-mining-titles
nsw_titles_data_source = DataSource(
    name="nsw-titles-csg-petroleum",
    file_path="NSW-titles-csg-petroleum.geojson",
    fetch=fetch_nsw_titles,
    parse=parse_geo,
)
