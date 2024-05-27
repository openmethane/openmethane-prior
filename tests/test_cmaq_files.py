import pytest
import os
import dotenv
import xarray as xr
import subprocess

# TODO Update this test when file structure is clear.
# This test ensures that the grid size for all input files is 10 km.
# When we re-arrange the files and scripts there may be other
# thing we want to test as well.
def test_grid_size_for_cmaq_files(root_dir, monkeypatch):

    expected_cell_size = 10000

    monkeypatch.chdir(root_dir)

    dotenv.load_dotenv()
    getenv = os.environ.get

    cmaqExamplePath = getenv("CMAQ_EXAMPLE")

    croFilePath = os.path.join(cmaqExamplePath, getenv("CROFILE"))
    dotFilePath = os.path.join(cmaqExamplePath, getenv("DOTFILE"))
    geomFilePath = os.path.join(cmaqExamplePath, getenv("GEO_EM"))

    with xr.open_dataset(geomFilePath) as geomXr :
        assert geomXr.DX == expected_cell_size
        assert geomXr.DY == expected_cell_size

    with xr.open_dataset(dotFilePath) as dotXr :
        assert dotXr.XCELL == expected_cell_size
        assert dotXr.YCELL == expected_cell_size

    with xr.open_dataset(croFilePath) as croXr :
        assert croXr.XCELL == expected_cell_size
        assert croXr.YCELL == expected_cell_size
