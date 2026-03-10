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
import numpy as np
import restapi # https://github.com/Bolton-and-Menk-GIS/restapi
import json

from openmethane_prior.lib import DataSource
from openmethane_prior.lib.data_manager.parsers import parse_geo
from openmethane_prior.lib.data_manager.source import ConfiguredDataSource


# Queensland borehole series - REST Service (ArcGIS)
# https://www.data.qld.gov.au/dataset/queensland-borehole-series/resource/c206a53a-59de-48c2-9544-b7b7323ed5dd
def fetch_qld_boreholes(data_source: ConfiguredDataSource):
    # qld_spatial_arcgis = restapi.ArcServer(url="https://spatial-gis.information.qld.gov.au/arcgis/rest/services")
    qld_spatial_boreholes = restapi.MapService(
        url="https://spatial-gis.information.qld.gov.au/arcgis/rest/services/GeoscientificInformation/Boreholes/MapServer"
    )

    boreholes_features = None
    oil_gas_layers = ["Boreholes CSG", "Boreholes Gas or Gas Show", "Boreholes Oil or Oil Show", "Boreholes Petroleum"]
    for layer_name in oil_gas_layers:
        boreholes_layer = qld_spatial_boreholes.layer(layer_name)
        # print(boreholes_layer.list_fields())

        layer_features = boreholes_layer.query(
            # TODO: filter out non-relevant results
            # where="bore_type in ('COAL SEAM GAS','GREENHOUSE GAS STORAGE','PETROLEUM','UNCONVENTIONAL PETROLEUM')",
            # this dataset has many fields, but we only need locations
            fields=[
                "bore_name",
                "bore_subtype",
                "bore_type",
                "borehole_pid",
                "operator_name",
                "result",
                "rig_release_date",
                "status",
                "tenure_no",
                "tenure_type",
            ],
            exceed_limit=True,
        )

        if boreholes_features is None:
            boreholes_features = layer_features
        else:
            boreholes_features.features.extend(layer_features.features)

    with open(data_source.asset_path, "w") as asset_file:
        json.dump(boreholes_features.json, asset_file)
        return data_source.asset_path


def parse_qld_boreholes(data_source: ConfiguredDataSource):
    boreholes_df = parse_geo(data_source=data_source)

    # lease/tenement name, i.e. "PL 100", is more useful than "PL" and 100.0,
    # so combine tenure_no and tenure_type into a single string
    boreholes_df["tenure"] = [
        None if t_no is np.nan else f"{t_type} {t_no:0.0f}"
        for t_no, t_type in boreholes_df[["tenure_no", "tenure_type"]].values
    ]

    return boreholes_df

# Locations of all boreholes in the Australian state of Queensland, via the
# Queensland Open Data Portal.
# Source: https://www.data.qld.gov.au/dataset/queensland-borehole-series
qld_boreholes_data_source = DataSource(
    name="qld-boreholes",
    file_path="QLD-boreholes.geojson",
    fetch=fetch_qld_boreholes,
    parse=parse_qld_boreholes,
)
