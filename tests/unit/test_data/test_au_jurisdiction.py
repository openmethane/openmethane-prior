import geopandas as gpd
import pytest
from shapely.geometry import Point, Polygon

from openmethane_prior.data_sources.au_shapes import au_jurisdiction_geometry


@pytest.fixture()
def states():
    # a 10x10 "mainland" with a bay cut into its east coast at x 8..10, y 4..6
    land = Polygon([(0, 0), (10, 0), (10, 4), (8, 4), (8, 6), (10, 6), (10, 10), (0, 10)])
    return gpd.GeoDataFrame({"name": ["Mainland"]}, geometry=[land], crs="EPSG:3577")


@pytest.fixture()
def territorial_sea():
    # 2 unit ring seaward of a baseline which closes the bay at x=10, so the
    # bay is internal waters and appears as part of the ring's hole
    baseline = [(0, 0), (10, 0), (10, 10), (0, 10)]
    ring = Polygon([(-2, -2), (12, -2), (12, 12), (-2, 12)], holes=[baseline])
    return gpd.GeoDataFrame({"name": ["Territorial sea"]}, geometry=[ring], crs="EPSG:3577")


@pytest.fixture()
def offshore_areas():
    # Commonwealth petroleum area east of the territorial sea, out to x=30
    area = Polygon([(12, -2), (30, -2), (30, 12), (12, 12)])
    return gpd.GeoDataFrame({"name": ["Offshore area"]}, geometry=[area], crs="EPSG:3577")


def test_jurisdiction_includes_land_internal_waters_and_seas(
    states, territorial_sea, offshore_areas
):
    jurisdiction = au_jurisdiction_geometry(
        states=states,
        territorial_sea=territorial_sea,
        offshore_areas=offshore_areas,
    )

    assert jurisdiction.contains(Point(5, 5))  # land
    assert jurisdiction.contains(Point(9, 5))  # internal waters in the bay
    assert jurisdiction.contains(Point(11, 5))  # territorial sea
    assert jurisdiction.contains(Point(20, 5))  # offshore petroleum area
    assert not jurisdiction.contains(Point(40, 5))  # beyond the offshore area
    assert not jurisdiction.contains(Point(5, 20))  # beyond the territorial sea


def test_jurisdiction_has_no_holes(states, territorial_sea, offshore_areas):
    jurisdiction = au_jurisdiction_geometry(
        states=states,
        territorial_sea=territorial_sea,
        offshore_areas=offshore_areas,
    )

    assert jurisdiction.geom_type == "Polygon"
    assert len(jurisdiction.interiors) == 0
