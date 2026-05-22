import datetime
from math import nan

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from openmethane_prior.sectors.oil_gas.emission_source import normalise_emission_source_df, \
    allocate_emissions_to_sources


def test_normalise_emission_source():
    test_df = gpd.GeoDataFrame({
        "geometry": [shapely.Point(1.0, 2.0)],
        "site_type": ["drillhole-csg"],
        "activity_start": [np.datetime64(datetime.datetime(2022, 1, 1, 0, 0))],
        "activity_end": [np.datetime64(datetime.datetime(2024, 1, 1, 0, 0))],
        "data_source": ["nsw-drillholes"],
        "data_source_id": ["012345"],
        "group_id": ["xyz"],
        "state": ["VIC"],
        "extra_column": [0],
    }, crs="EPSG:7844")

    result_df = normalise_emission_source_df(test_df, "EPSG:4326")

    assert list(result_df.columns) == [
        "geometry",
        "site_type",
        "activity_start",
        "activity_end",
        "data_source",
        "data_source_id",
        "group_id",
        "state",
    ]

    assert result_df.crs == "EPSG:4326"


def test_allocate_emissions_to_sources_only_masked():
    df = pd.DataFrame(
        data=[
            (None, "drillhole-csg"),
            (0, "drillhole-csg"),
            (0, "drillhole-unknown"),
            (None, None),
        ],
        columns=["emissions_quantity", "site_type"],
    )
    mask = df["site_type"] == "drillhole-csg"

    allocate_emissions_to_sources(df, mask, 1)

    assert df["emissions_quantity"].sum() == 1
    # allocated sources get an equal share of emissions
    assert (df[mask]["emissions_quantity"] == 0.5).all()
    # unallocated sources are not modified
    assert np.isnan(df["emissions_quantity"].iloc[3])


def test_allocate_emissions_to_sources_additive():
    df = pd.DataFrame(
        data=[
            (2.1, "drillhole-csg"),
            (0, "drillhole-csg"),
            (None, "drillhole-csg"),
        ],
        columns=["emissions_quantity", "site_type"],
    )
    mask = df["site_type"] == "drillhole-csg"

    allocate_emissions_to_sources(df, mask, 3)

    assert df["emissions_quantity"].sum() == 3 + 2.1
    # allocated sources get an equal share of emissions
    assert list(df[mask]["emissions_quantity"]) == [3.1, 1, 1]
