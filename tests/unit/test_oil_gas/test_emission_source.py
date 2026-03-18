import datetime
import geopandas as gpd
import numpy as np
import shapely

from openmethane_prior.sectors.oil_gas.emission_sources.emission_source import normalise_emission_source_df


def test_normalise_emission_source():
    test_df = gpd.GeoDataFrame({
        "geometry": [shapely.Point(1.0, 2.0)],
        "site_type": ["drillhole-csg"],
        "activity_start": [np.datetime64(datetime.datetime(2022, 1, 1, 0, 0))],
        "activity_end": [np.datetime64(datetime.datetime(2024, 1, 1, 0, 0))],
        "data_source": ["nsw-drillholes"],
        "data_source_id": ["012345"],
        "group_id": ["xyz"],
        "extra_column": [0],
    }, crs="EPSG:7844")

    result_df = normalise_emission_source_df(test_df)

    assert list(result_df.columns) == [
        "geometry",
        "site_type",
        "activity_start",
        "activity_end",
        "data_source",
        "data_source_id",
        "group_id",
    ]

    assert result_df.crs == "EPSG:4326"
