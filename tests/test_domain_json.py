# work around until folder structure is updated
import json
from io import StringIO

import pytest
from scripts.omDomainJSON import write_domain_json


def test_001_json_structure(config, input_domain):
    input_domain.to_netcdf(config.input_domain_file)

    if not config.input_domain_file.exists():
        pytest.mark.skip("Missing domain file")

    outfile = StringIO()

    # generate the JSON, writing to a memory buffer
    write_domain_json(config, outfile)

    outfile.seek(0)
    domain = json.load(outfile)

    # spot check some known values
    assert domain["crs"] == {
        "projection_type": "lambert_conformal_conic",
        "standard_parallel": -15.0,
        "standard_parallel_2": -40.0,
        "longitude_of_central_meridian": 133.302001953125,
        "latitude_of_projection_origin": -27.643997192382812,
        "projection_origin_x": -2270000,
        "projection_origin_y": -2165629.25,
        "proj4": "+proj=lcc +lat_0=-27.6439971923828 +lon_0=133.302001953125 +lat_1=-15 +lat_2=-40 +x_0=0 +y_0=0 +R=6370000 +units=m +no_defs",  # noqa: E501
    }
    assert domain["grid_properties"] == {
        "rows": 430,
        "cols": 454,
        "cell_x_size": 10000.0,
        "cell_y_size": 10000.0,
        "center_latlon": [133.302001953125, -27.5],
    }

    # Check the number of cells
    assert (
        len(domain["grid_cells"])
        == domain["grid_properties"]["rows"] * domain["grid_properties"]["cols"]
    )
    # check a single grid cell for known values
    assert domain["grid_cells"][0] == {
        "projection_x_coordinate": 0,
        "projection_y_coordinate": 0,
        "landmask": 0,
        "center_latlon": [-44.73386001586914, 105.03723907470703],
        "corner_latlons": [
            [-44.76662826538086, 104.96293640136719],
            [-44.78663635253906, 105.08344268798828],
            [-44.70106506347656, 105.11154174804688],
            [-44.681068420410156, 104.99114990234375],
        ],
    }
