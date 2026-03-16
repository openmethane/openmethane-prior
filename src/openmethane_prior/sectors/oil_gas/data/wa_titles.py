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
import pandas as pd
import restapi # https://github.com/Bolton-and-Menk-GIS/restapi

from openmethane_prior.lib import DataSource
from openmethane_prior.lib.data_manager.parsers import parse_geo
from openmethane_prior.lib.data_manager.source import ConfiguredDataSource
from .esri_types import map_esri_date_to_str


# WA Petroleum Titles (DMIRS-011) - REST Service (ArcGIS)
# https://catalogue.data.wa.gov.au/dataset/wa-petroleum-titles-dmirs-011/resource/f5bb4e83-241e-4dcf-8efe-41707866af4e
def fetch_wa_titles(data_source: ConfiguredDataSource):
    # wa_arcgis = restapi.ArcServer(url="https://public-services.slip.wa.gov.au/public/rest/services")
    wa_arcgis_mining = restapi.MapService(
        url="https://public-services.slip.wa.gov.au/public/rest/services/SLIP_Public_Services/Industry_and_Mining/MapServer"
    )

    # DMIRS-011 contains current active petroleum titles, but has expired
    # titles periodically removed. Our interest is only in "Production License"
    # titles, as we wouldn't expect significant emissions during exploration,
    # or if the parcel of land is on a "retention" lease.
    titles_layer = wa_arcgis_mining.layer("WA Petroleum Titles (DMIRS-011)")
    titles_features = titles_layer.query(
        where="type in ('Production Licence')",
        fields=[
            "title_id",
            "type",
            "issued",
            "expiry",
        ],
        exceed_limit=True,
    )
    titles_df = gpd.GeoDataFrame.from_features(titles_features.features)

    # Rename some fields so that they match DMIRS-051
    titles_df = titles_df.rename(columns={
        "issued": "issued_date",
        "expiry": "end_date",
    })

    # DMIRS-051 contains the record of previous titles. One parcel of land
    # can appear in this dataset multiple times as titles change. Sometimes a
    # single parcel can have multiple titles with the same dates or overlapping
    # dates. No attempt is made to filter or de-duplicate these at this stage.
    historic_titles_layer = wa_arcgis_mining.layer("WA Petroleum - Historical Titles (DMIRS-051)")
    historic_titles_features = historic_titles_layer.query(
        where="type in ('Production Licence')",
        fields=[
            "title_id",
            "type",
            "issued_date",
            "end_date",
        ],
        exceed_limit=True,
    )
    historic_df = gpd.GeoDataFrame.from_features(historic_titles_features.features)

    # combine current and historic title datasets
    df = pd.concat([titles_df, historic_df])

    # convert date fields to RFC3339
    df["issued_date"] = df["issued_date"].map(map_esri_date_to_str)
    df["end_date"] = df["end_date"].map(map_esri_date_to_str)

    with open(data_source.asset_path, "w") as asset_file:
        asset_file.write(df.to_json())
        return data_source.asset_path


# Locations of all petroleum titles in the Australian state of Western
# Australia via the Data WA Portal.
# Source: https://catalogue.data.wa.gov.au/dataset/wa-petroleum-titles-dmirs-011
wa_titles_data_source = DataSource(
    name="wa-petroleum-titles",
    file_path="WA-petroleum-titles.geojson",
    fetch=fetch_wa_titles,
    parse=parse_geo,
)
