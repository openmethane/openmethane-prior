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
from openmethane_prior.sectors.oil_gas.data.esri_types import map_esri_date_to_str


# Petroleum leases - Queensland - REST Service (ArcGIS)
# https://www.data.qld.gov.au/dataset/queensland-mining-and-exploration-tenure-series/resource/544ecb39-9c25-42f9-9928-b44c7ff05b30
def fetch_qld_leases(data_source: ConfiguredDataSource):
    # qld_spatial_arcgis = restapi.ArcServer(url="https://spatial-gis.information.qld.gov.au/arcgis/rest/services")
    qld_current_leases = restapi.MapService(
        url="https://spatial-gis.information.qld.gov.au/arcgis/rest/services/Economy/MinesPermitsCurrent/MapServer"
    )
    qld_historic_leases = restapi.MapService(
        url="https://spatial-gis.information.qld.gov.au/arcgis/rest/services/Economy/MinesPermitsHistoric/MapServer"
    )

    fields = [
        "displayname",
        "permittype",
        "permitstatus",
        "approvedate",
        "expirydate",
        "permitminerals",
        "permitpurpose",
    ]

    leases_layer = qld_current_leases.layer("PL granted")
    leases_features = leases_layer.query(
        fields=fields,
        exceed_limit=True,
    )
    historic_layer = qld_historic_leases.layer("Historical petroleum lease")
    historic_features = historic_layer.query(
        fields=fields,
        exceed_limit=True,
    )

    df = pd.concat([
        gpd.GeoDataFrame.from_features(leases_features.features),
        gpd.GeoDataFrame.from_features(historic_features.features),
    ])

    df["approvedate"] = df["approvedate"].map(map_esri_date_to_str)
    df["expirydate"] = df["expirydate"].map(map_esri_date_to_str)

    with open(data_source.asset_path, "w") as asset_file:
        asset_file.write(df.to_json())
        return data_source.asset_path



def parse_qld_leases(data_source: ConfiguredDataSource):
    leases_df = parse_geo(data_source=data_source)

    # lease/tenement name, i.e. "PL 100", is more useful than "PL" and 100.0,
    # so combine tenure_no and tenure_type into a single string
    # leases_df["tenure"] = [
    #     None if t_no is np.nan else f"{t_type} {t_no:0.0f}"
    #     for t_no, t_type in leases_df[["tenure_no", "tenure_type"]].values
    # ]

    return leases_df

# Locations of all mining leases in the Australian state of Queensland, via the
# Queensland Open Data Portal.
# Source: https://www.data.qld.gov.au/dataset/queensland-mining-and-exploration-tenure-series
qld_leases_data_source = DataSource(
    name="qld-leases",
    file_path="QLD-leases.geojson",
    fetch=fetch_qld_leases,
    parse=parse_qld_leases,
)
