import os

import pytest
import xarray as xr
from openmethane_prior.omUtils import getenv
from scripts.omCreateDomainInfo import create_domain_info


@pytest.fixture()
def geom_xr(root_dir):
    geom_file_path = os.path.join(root_dir, getenv("GEO_EM"))
    return xr.open_dataset(geom_file_path)


@pytest.fixture()
def input_domain_xr(root_dir):
    return create_domain_info(
        geometry_file=os.path.join(root_dir, getenv("GEO_EM")),
        cross_file=os.path.join(root_dir, getenv("CROFILE")),
        dot_file=os.path.join(root_dir, getenv("DOTFILE")),
    )


def test_grid_size_for_geo_files(cro_xr, geom_xr, dot_xr):
    expected_cell_size = 10000

    assert cro_xr.XCELL == expected_cell_size
    assert cro_xr.YCELL == expected_cell_size

    assert geom_xr.DX == expected_cell_size
    assert geom_xr.DY == expected_cell_size

    assert dot_xr.XCELL == expected_cell_size
    assert dot_xr.YCELL == expected_cell_size


def test_compare_in_domain_with_cro_dot_files(input_domain_xr, cro_xr, dot_xr):
    assert dot_xr.NCOLS == input_domain_xr.COL_D.size
    assert dot_xr.NROWS == input_domain_xr.ROW_D.size

    assert cro_xr.NCOLS == input_domain_xr.COL.size
    assert cro_xr.NROWS == input_domain_xr.ROW.size
