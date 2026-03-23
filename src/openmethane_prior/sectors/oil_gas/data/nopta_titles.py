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
import json
import restapi # https://github.com/Bolton-and-Menk-GIS/restapi

from openmethane_prior.lib import DataSource, ConfiguredDataSource
from openmethane_prior.lib.data_manager.parsers import parse_geo

from .esri_types import map_esri_date_to_str


def fetch_nopta_titles(data_source: ConfiguredDataSource):
    nopta_titles = restapi.MapService(
        url="https://arcgis.nopta.gov.au/arcgis/rest/services/Public/TitlesCompany_NOPTA/MapServer"
    )

    titles_layer = nopta_titles.layer("Titles and Permits Current")

    layer_features = titles_layer.query(
        # where="Type in ('Petroleum','Mineral or Coal') AND Purpose in ('Development','Appraisal', 'Exploration')",
        # descriptions of available fields
        # https://www.nopta.gov.au/maps-and-public-data/documents/DataDescription_OffshorePetroleumWells.docx
        fields=[
            "OBJECTID",
            "Title",
            "RelTitle",
            "TitleType",
            "ExpiryDate",
            "GrantDate",
            "LastReDate",
            "NoOfRenews",
            "EndDate",
            "Status",
            "FieldName",
            "BasinName",
            "SubBasin",
            "OffShoreAr",
            "TitleOprat",
            "TitleHold",
            "NoOfBlocks",
            "AreaKM2",
            "NEATS_Links",
            "TITLE_NUMBER_NEATS",
        ],
        exceed_limit=True,
    )

    for feature in layer_features["features"]:
        # convert esriFieldTypeDate to RFC3339 date
        for feature_key in feature["properties"]:
            if feature_key.endswith("Date"):
                feature["properties"][feature_key] = map_esri_date_to_str(feature["properties"][feature_key])

    with open(data_source.asset_path, "w") as asset_file:
        json.dump(layer_features.json, asset_file)
        return data_source.asset_path


offshore_area_state_mapping = {
    "Western Australia": "WA",
    "Victoria": "VIC",
    "Northern Territory": "NT",
    "Queensland": "QLD",
    "South Australia": "SA",
    "Tasmania": "TAS",
    "New South Wales": "NSW",
    "ACT": "ACT",
    # https://www.infrastructure.gov.au/territories-regions/territories/ashmore-and-cartier-islands
    "Territory of Ashmore and Cartier Islands": "NT",
    "Outside of Australia": None,
    "UNK": None,
}
def map_offshore_area_to_state(offshore_area: str) -> str | None:
    if offshore_area in offshore_area_state_mapping:
        return offshore_area_state_mapping[offshore_area]
    return None


def parse_nopta_titles(data_source: ConfiguredDataSource):
    df = parse_geo(data_source=data_source)

    # # NOPIMS dataset may record multiple boreholes for a single well, all
    # # with identical WellName and location. This will remove duplicate rows
    # # so that only a single location is present for each well, keeping the
    # # earliest "RigReleaseDate" when the first bore was drilled at the well.
    # wells_df = wells_df.sort_values(by="RigReleaseDate")
    # wells_df.drop_duplicates(subset="WellName", keep="first", inplace=True)
    #
    df["state"] = df["OffShoreAr"].map(map_offshore_area_to_state)

    return df


# Locations of all offshore petroleum and gas titles (licenses) administered
# by the National Offshore Petroleum Titles Administrator (NOPTA), via the
# National Electronic Approvals Tracking System (NEATS).
# Source: https://www.nopta.gov.au/maps-and-public-data/neats-info.html
nopta_titles_data_source = DataSource(
    name="NOPTA-titles",
    file_path="NOPTA-titles.geojson",
    fetch=fetch_nopta_titles,
    parse=parse_nopta_titles,
)
