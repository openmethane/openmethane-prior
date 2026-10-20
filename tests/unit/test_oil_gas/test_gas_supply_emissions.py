import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from openmethane_prior.lib.grid.grid import Grid
from openmethane_prior.sectors.oil_gas.safeguard import gas_supply_emissions


def test_gas_supply_emissions():
    domain_grid = Grid(dimensions=(4, 4), origin_xy=(0, 0), cell_size=(1, 1))
    # one state covering the four inner cells of the grid
    au_states = gpd.GeoDataFrame(
        {"short_name": ["NSW"]},
        geometry=[shapely.box(1, 1, 3, 3)],
        crs="EPSG:4326",
    )
    facilities_df = pd.DataFrame({"state": ["NSW", "NSW"], "ch4_kg": [100.0, 50.0]})
    nightlights = np.arange(1, 17, dtype=np.float64).reshape(4, 4)

    result = gas_supply_emissions(
        domain_grid=domain_grid,
        facilities_df=facilities_df,
        au_states=au_states,
        nightlights=nightlights,
    )

    assert result.shape == domain_grid.shape
    np.testing.assert_approx_equal(result.sum(), 150.0)
    # cells outside the state receive no emissions
    assert result[0, :].sum() == 0
    assert result[:, 0].sum() == 0
    assert result[3, :].sum() == 0
    assert result[:, 3].sum() == 0
    # inner cells are allocated in proportion to their night lights
    inner = nightlights[1:3, 1:3]
    np.testing.assert_allclose(result[1:3, 1:3], 150.0 * inner / inner.sum())
