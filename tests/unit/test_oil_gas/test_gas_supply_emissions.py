import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from shapely.geometry import Polygon

from openmethane_prior.lib.grid.grid import Grid
from openmethane_prior.sectors.oil_gas.safeguard import gas_supply_emissions


@pytest.fixture
def grid():
    return Grid(dimensions=(4, 4), origin_xy=(0, 0), cell_size=(1, 1))


@pytest.fixture
def states():
    # one state covering the four inner cells of the grid
    return gpd.GeoDataFrame(
        {"short_name": ["NSW"]},
        geometry=[Polygon([(1, 1), (3, 1), (3, 3), (1, 3)])],
        crs="EPSG:4326",
    )


@pytest.fixture
def facilities():
    return pd.DataFrame({"state": ["NSW", "NSW"], "ch4_kg": [100.0, 50.0]})


@pytest.fixture
def nightlights_values():
    return np.arange(1, 17, dtype=float).reshape(4, 4)


def test_nightlights_as_ndarray(grid, states, facilities, nightlights_values):
    result = gas_supply_emissions(grid, facilities, states, nightlights_values)

    assert result.shape == grid.shape
    np.testing.assert_approx_equal(result.sum(), 150.0)
    # cells outside the state get nothing
    assert result[0, :].sum() == 0
    assert result[:, 0].sum() == 0


def test_nightlights_as_dataarray(grid, states, facilities, nightlights_values):
    as_array = gas_supply_emissions(grid, facilities, states, nightlights_values)
    as_dataarray = gas_supply_emissions(
        grid, facilities, states, xr.DataArray(nightlights_values, dims=("y", "x")),
    )

    np.testing.assert_allclose(as_dataarray, as_array)
