import pytest
import xarray as xr


@pytest.fixture()
def geom_xr(config):
    return xr.open_dataset(config.geometry_file)


def test_grid_size_for_geo_files(cro_xr, geom_xr, dot_xr):
    expected_cell_size = 10000

    assert cro_xr.XCELL == expected_cell_size
    assert cro_xr.YCELL == expected_cell_size

    assert geom_xr.DX == expected_cell_size
    assert geom_xr.DY == expected_cell_size

    assert dot_xr.XCELL == expected_cell_size
    assert dot_xr.YCELL == expected_cell_size


def test_compare_in_domain_with_cro_dot_files(input_domain, cro_xr, dot_xr):
    assert dot_xr.NCOLS == input_domain.COL_D.size
    assert dot_xr.NROWS == input_domain.ROW_D.size

    assert cro_xr.NCOLS == input_domain.COL.size
    assert cro_xr.NROWS == input_domain.ROW.size
