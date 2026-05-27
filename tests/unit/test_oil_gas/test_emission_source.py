import datetime
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from openmethane_prior.sectors.oil_gas.emission_source import (
    normalise_emission_source_df,
    allocate_emissions_to_sources,
)


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
        "weight",
    ]

    assert result_df["weight"].sum() == 1.0

    assert result_df.crs == "EPSG:4326"


def test_allocate_emissions_to_sources_only_masked():
    df = pd.DataFrame(
        data=[
            (None, "drillhole-csg", 1.0),
            (0, "drillhole-csg", 1.0),
            (0, "drillhole-unknown", 1.0),
            (None, None, 1.0),
        ],
        columns=["emissions_quantity", "site_type", "weight"],
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
            (2.1, "drillhole-csg", 1.0),
            (0, "drillhole-csg", 1.0),
            (None, "drillhole-csg", 1.0),
        ],
        columns=["emissions_quantity", "site_type", "weight"],
    )
    mask = df["site_type"] == "drillhole-csg"

    allocate_emissions_to_sources(df, mask, 3)

    assert df["emissions_quantity"].sum() == 3 + 2.1
    # allocated sources get an equal share of emissions
    assert list(df[mask]["emissions_quantity"]) == [3.1, 1, 1]


def test_allocate_emissions_to_sources_facilities():
    df = pd.DataFrame(
        data=[
            (0, "drillhole-csg", True, 1.0),
            (0, "drillhole-csg", True, 1.0),
            (0, "drillhole-csg", True, 1.0),
            (0, "facility-unknown", True, 1.0),
            (0, None, True, 1.0),
            (0, "drillhole-csg", False, 1.0),
            (0, "facility-unknown", False, 1.0),
        ],
        columns=["emissions_quantity", "site_type", "masked", "weight"],
    )

    allocate_emissions_to_sources(df, df["masked"], 12)

    np.testing.assert_approx_equal(df["emissions_quantity"].sum(), 12)

    assert list(df[df["masked"]]["emissions_quantity"]) == [2, 2, 2, 3, 3]

    # equal emissions allocated to the set of drillholes and the set of
    # facilities
    drillholes_mask = df["site_type"] == "drillhole-csg"
    np.testing.assert_approx_equal(
        df[drillholes_mask]["emissions_quantity"].sum(),
        df[~drillholes_mask]["emissions_quantity"].sum()
    )


def test_allocate_emissions_to_sources_pipelines():
    df = pd.DataFrame(
        data=[
            (0, "drillhole-csg", True, 1.0),
            (0, "drillhole-csg", True, 1.0),
            (0, "pipeline-gas", True, 1.0),
            (0, "drillhole-csg", False, 1.0),
            (0, "pipeline-gas", False, 1.0),
        ],
        columns=["emissions_quantity", "site_type", "masked", "weight"],
    )

    allocate_emissions_to_sources(df, df["masked"], 4)

    np.testing.assert_approx_equal(df["emissions_quantity"].sum(), 4)

    assert list(df[df["masked"]]["emissions_quantity"]) == [1, 1, 2]

    # equal emissions allocated to the set of drillholes and the set of
    # pipelines
    drillholes_mask = df["site_type"] == "drillhole-csg"
    np.testing.assert_approx_equal(
        df[drillholes_mask]["emissions_quantity"].sum(),
        df[~drillholes_mask]["emissions_quantity"].sum()
    )


def test_allocate_emissions_to_sources_multiple():
    df = pd.DataFrame(
        data=[
            (0, "drillhole-csg", True, 1.0),
            (0, "drillhole-csg", True, 1.0),
            (0, "drillhole-csg", True, 1.0),
            (0, "drillhole-csg", True, 1.0),
            (0, "pipeline-gas", True, 1.0),
            (0, "pipeline-gas", True, 1.0),
            (0, "facility-unknown", True, 1.0),
            (0, "drillhole-csg", False, 1.0),
            (0, "pipeline-gas", False, 1.0),
        ],
        columns=["emissions_quantity", "site_type", "masked", "weight"],
    )

    allocate_emissions_to_sources(df, df["masked"], 12)

    np.testing.assert_approx_equal(df["emissions_quantity"].sum(), 12)

    assert list(df[df["masked"]]["emissions_quantity"]) == [1, 1, 1, 1, 2, 2, 4]

    # equal emissions allocated to the set of drillholes and the set of
    # pipelines
    drillholes_mask = df["site_type"] == "drillhole-csg"
    pipelines_mask = df["site_type"] == "pipeline-gas"
    facilities_mask = df["site_type"] == "facility-unknown"
    np.testing.assert_approx_equal(
        df[drillholes_mask]["emissions_quantity"].sum(),
        df[pipelines_mask]["emissions_quantity"].sum()
    )
    np.testing.assert_approx_equal(
        df[drillholes_mask]["emissions_quantity"].sum(),
        df[facilities_mask]["emissions_quantity"].sum()
    )


def test_allocate_emissions_to_sources_weights():
    df = pd.DataFrame(
        data=[
            (0, "drillhole-csg", True, 1.0),
            (0, "drillhole-csg", True, 1.0),
            (0, "drillhole-csg", True, 1.0),
            (0, "drillhole-csg", True, 1.0),
            (0, "pipeline-gas", True, 2.0),
            (0, "pipeline-gas", True, 6.0),
            (0, "facility-unknown", True, 0.5),
            (0, "facility-unknown", True, 3.5),
            (0, "drillhole-csg", False, 1.0),
            (0, "pipeline-gas", False, 1.0),
        ],
        columns=["emissions_quantity", "site_type", "masked", "weight"],
    )

    allocate_emissions_to_sources(df, df["masked"], 12)

    np.testing.assert_approx_equal(df["emissions_quantity"].sum(), 12)

    assert list(df[df["masked"]]["emissions_quantity"]) == [1.0, 1.0, 1.0, 1.0, 1.0, 3.0, 0.5, 3.5]

    # equal emissions allocated to the set of drillholes and the set of
    # pipelines
    drillholes_mask = df["site_type"] == "drillhole-csg"
    pipelines_mask = df["site_type"] == "pipeline-gas"
    facilities_mask = df["site_type"] == "facility-unknown"
    np.testing.assert_approx_equal(
        df[drillholes_mask]["emissions_quantity"].sum(),
        df[pipelines_mask]["emissions_quantity"].sum()
    )
    np.testing.assert_approx_equal(
        df[drillholes_mask]["emissions_quantity"].sum(),
        df[facilities_mask]["emissions_quantity"].sum()
    )
