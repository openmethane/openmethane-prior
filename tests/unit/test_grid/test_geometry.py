import math

import numpy as np
import shapely
from shapely.geometry.polygon import Polygon

from openmethane_prior.lib.grid.geometry import polygon_cell_intersection


def test_polygon_cell_intersection(aust10km_grid):
    # Australian Capital Territory polygon, with a hole for Lake Burley Griffin
    act_polygon = shapely.Polygon(
        shell=[
            [149.399284, -35.319175], [149.352134, -35.351317], [149.336502, -35.339914], [149.254815, -35.330079], [149.207546, -35.345305], [149.146586, -35.414836], [149.139052, -35.432543], [149.155134, -35.436628], [149.135550, -35.454422], [149.151279, -35.506926], [149.131376, -35.554173], [149.142510, -35.592570], [149.084514, -35.580594], [149.078043, -35.586127], [149.087612, -35.639697], [149.097495, -35.647313], [149.095379, -35.679285], [149.109483, -35.696640], [149.090716, -35.765600], [149.101481, -35.803698], [149.093517, -35.824221], [149.095682, -35.845716], [149.064408, -35.874932], [149.048811, -35.920410], [149.012198, -35.899697], [148.959133, -35.895456], [148.909367, -35.853065], [148.907065, -35.829563], [148.886623, -35.810063], [148.897776, -35.794650], [148.894887, -35.771654], [148.903348, -35.757798], [148.894087, -35.751288], [148.886633, -35.719136], [148.877693, -35.714936], [148.872491, -35.721422], [148.855652, -35.760874], [148.856132, -35.753518], [148.835715, -35.741884], [148.822423, -35.720900], [148.791182, -35.703449], [148.798434, -35.666492], [148.767495, -35.647323], [148.783462, -35.628342], [148.768473, -35.603186], [148.788758, -35.588179], [148.773039, -35.568157], [148.778231, -35.558852], [148.769231, -35.544096], [148.772364, -35.529329], [148.762675, -35.495505], [148.774354, -35.486003], [148.767058, -35.465405], [148.788868, -35.426382], [148.785764, -35.408748], [148.796119, -35.406549], [148.795719, -35.392920], [148.808702, -35.382373], [148.793247, -35.339156], [148.807854, -35.309647], [149.120902, -35.124517], [149.138819, -35.128466], [149.138600, -35.135257], [149.149637, -35.138669], [149.146775, -35.144856], [149.164312, -35.142046], [149.167696, -35.159881], [149.189097, -35.165677], [149.183629, -35.175618], [149.197037, -35.185499], [149.189701, -35.203308], [149.208568, -35.211501], [149.204883, -35.229549], [149.214063, -35.219507], [149.238597, -35.222127], [149.246790, -35.229217], [149.234884, -35.242822], [149.273132, -35.259287], [149.272048, -35.273644], [149.315286, -35.276286], [149.322394, -35.286708], [149.341384, -35.286648], [149.361948, -35.308998], [149.394790, -35.303157], [149.399284, -35.319175]
        ],
        holes=[
            [[149.153176, -35.304976], [149.136510, -35.289256], [149.122879, -35.286560], [149.118459, -35.293608], [149.110274, -35.284577], [149.114443, -35.280492], [149.103116, -35.285130], [149.101406, -35.294277], [149.099252, -35.285600], [149.088030, -35.285150], [149.083012, -35.296961], [149.071123, -35.298567], [149.084355, -35.303898], [149.095399, -35.287391], [149.101389, -35.301479], [149.126110, -35.294247], [149.144619, -35.310156], [149.153176, -35.304976]]
        ]
    )

    test_intersection = polygon_cell_intersection(act_polygon, aust10km_grid)

    assert len(test_intersection) == 41 # 41 cells intersecting
    # spot test the first and last intersecting cells coordinates and coverage
    assert test_intersection[0][0] == (366, 115)
    assert math.isclose(test_intersection[0][1], 0.00018735184840114796)
    assert test_intersection[-1][0] == (368, 124)
    assert math.isclose(test_intersection[-1][1], 0.010287626279578469)

    # ACT sits entirely within the aust10km grid, so the sum of intersections
    # should cover the entire shape of the polygon, adding up to 1
    test_coverage = np.sum([area_proportion for coords, area_proportion in test_intersection])
    assert math.isclose(test_coverage, 1)

    # Australian Capital Territory exterior polygon, without a hole
    act_exterior = Polygon(act_polygon.exterior.coords)
    test_exterior_intersection = polygon_cell_intersection(act_exterior, aust10km_grid)

    assert len(test_exterior_intersection) == 41

    # proportion of intersection is different for these cells since the lake is
    # no longer considered outside the geometry
    assert test_exterior_intersection[0][0] == (366, 115)
    assert math.isclose(test_exterior_intersection[0][1], 0.00018676566293762296)

    test_exterior_coverage = np.sum([area_proportion for coords, area_proportion in test_exterior_intersection])
    assert math.isclose(test_exterior_coverage, 1)

def test_polygon_cell_intersection_multipolygon(aust10km_grid):
    # 3 squares that roughly correspond to grid cells around Melbourne
    test_multi_polygon = shapely.MultiPolygon([
        [[(144.7992, -37.8467), (144.9135, -37.8382), (144.9027, -37.7479), (144.7885, -37.7564)]],
        [[(144.9135, -37.8382), (145.0278, -37.8296), (145.0169, -37.7394), (144.9027, -37.7479)]],
        [[(144.9243, -37.9284), (145.0387, -37.9199), (145.0278, -37.8296), (144.9135, -37.8382)]],
    ])

    test_intersection = polygon_cell_intersection(test_multi_polygon, aust10km_grid)

    assert len(test_intersection) == 8

    # spot test a few cells
    assert test_intersection[0][0] == (327, 98)
    assert math.isclose(test_intersection[0][1], 0.00015177599857517192)
    assert test_intersection[1][0] == (328, 98)
    assert math.isclose(test_intersection[1][1], 0.33307785884834573)
    assert test_intersection[-1][0] == (328, 100)
    assert math.isclose(test_intersection[-1][1], 0.00018626618857067368)

    # the entire shape fits in aust10km so should have 100% coverage
    test_coverage = np.sum([area_proportion for coords, area_proportion in test_intersection])
    assert math.isclose(test_coverage, 1)
