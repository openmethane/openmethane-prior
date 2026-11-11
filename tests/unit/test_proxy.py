import numpy as np
import shapely
import xarray as xr

from openmethane_prior.lib.grid.domain import Domain
from openmethane_prior.lib.grid.grid import Grid
from openmethane_prior.lib.proxy import GriddedProxy


def test_from_raster():
    inventory_grid = Grid(dimensions=(4, 4), origin_xy=(0, 0), cell_size=(1, 1))
    # the inventory region excludes the left column
    inventory_mask = np.ones(inventory_grid.shape)
    inventory_mask[:, 0] = 0
    inventory_domain = Domain(
        dataset=xr.Dataset({"inventory_mask": (("y", "x"), inventory_mask)}),
        grid=inventory_grid,
    )
    # the prior domain covers the left half of the inventory domain
    domain_grid = Grid(dimensions=(2, 4), origin_xy=(0, 0), cell_size=(1, 1))
    # a raster with four pixels in each grid cell, each with a value of 1
    pixel_coords = np.arange(0.25, 4, 0.5)
    raster = xr.DataArray(
        np.ones((8, 8)),
        coords={"y": pixel_coords, "x": pixel_coords},
    )

    result = GriddedProxy.from_raster(
        raster=raster,
        domain_grid=domain_grid,
        inventory_domain=inventory_domain,
    )

    assert result.domain_grid == domain_grid
    assert result.inventory_grid == inventory_grid
    np.testing.assert_allclose(result.domain_values, 4.0 * inventory_mask[:, 0:2])
    np.testing.assert_allclose(result.inventory_values, 4.0 * inventory_mask)


def test_distribute_whole_inventory_region():
    grid = Grid(dimensions=(4, 4), origin_xy=(0, 0), cell_size=(1, 1))
    values = np.arange(1, 17, dtype=np.float64).reshape(4, 4)
    proxy = GriddedProxy(
        domain_grid=grid,
        domain_values=values,
        inventory_grid=grid,
        inventory_values=values,
    )

    result = proxy.distribute(150.0)

    np.testing.assert_allclose(result, 150.0 * values / values.sum())


def test_distribute_partial_domain():
    inventory_grid = Grid(dimensions=(4, 4), origin_xy=(0, 0), cell_size=(1, 1))
    # the domain covers the left half of the inventory grid
    domain_grid = Grid(dimensions=(2, 4), origin_xy=(0, 0), cell_size=(1, 1))
    proxy = GriddedProxy(
        domain_grid=domain_grid,
        domain_values=np.ones(domain_grid.shape),
        inventory_grid=inventory_grid,
        inventory_values=np.ones(inventory_grid.shape),
    )

    result = proxy.distribute(160.0)

    # half the proxy falls in the domain, so it receives half the total
    np.testing.assert_allclose(result, 10.0)


def test_distribute_region():
    inventory_grid = Grid(dimensions=(4, 4), origin_xy=(0, 0), cell_size=(1, 1))
    # the domain covers the top right corner of the inventory grid
    domain_grid = Grid(dimensions=(2, 2), origin_xy=(2, 2), cell_size=(1, 1))
    inventory_values = np.arange(1, 17, dtype=np.float64).reshape(4, 4)
    proxy = GriddedProxy(
        domain_grid=domain_grid,
        domain_values=inventory_values[2:4, 2:4],
        inventory_grid=inventory_grid,
        inventory_values=inventory_values,
    )
    # the region covers the top half of the inventory grid
    region = shapely.box(0, 2, 4, 4)

    result = proxy.distribute(100.0, region=region)

    # each cell receives its share of the proxy over the whole region
    region_values = inventory_values[2:4, :]
    np.testing.assert_allclose(result, 100.0 * inventory_values[2:4, 2:4] / region_values.sum())


def test_distribute_region_outside_domain():
    inventory_grid = Grid(dimensions=(4, 4), origin_xy=(0, 0), cell_size=(1, 1))
    domain_grid = Grid(dimensions=(2, 2), origin_xy=(2, 2), cell_size=(1, 1))
    proxy = GriddedProxy(
        domain_grid=domain_grid,
        domain_values=np.ones(domain_grid.shape),
        inventory_grid=inventory_grid,
        inventory_values=np.ones(inventory_grid.shape),
    )
    # the region covers the bottom half of the inventory grid
    region = shapely.box(0, 0, 4, 2)

    result = proxy.distribute(100.0, region=region)

    np.testing.assert_allclose(result, 0.0)


def test_distribute_region_inventory_projection():
    # the domain grid uses GDA2020 lon/lat, the inventory grid WGS84 lon/lat
    domain_grid = Grid(
        dimensions=(4, 4), origin_xy=(140, -40), cell_size=(1, 1), proj_params="EPSG:7843"
    )
    inventory_grid = Grid(
        dimensions=(4, 4), origin_xy=(140, -40), cell_size=(1, 1), proj_params="EPSG:4326"
    )
    proxy = GriddedProxy(
        domain_grid=domain_grid,
        domain_values=np.ones(domain_grid.shape),
        inventory_grid=inventory_grid,
        inventory_values=np.ones(inventory_grid.shape),
    )
    # the region covers the bottom half of both grids, in domain coordinates
    region = shapely.box(140, -40, 144, -38)

    result = proxy.distribute(80.0, region=region)

    np.testing.assert_allclose(result[0:2, :], 10.0)
    np.testing.assert_allclose(result[2:4, :], 0.0)


def test_distribute_without_proxy_values():
    grid = Grid(dimensions=(4, 4), origin_xy=(0, 0), cell_size=(1, 1))
    proxy = GriddedProxy(
        domain_grid=grid,
        domain_values=np.zeros(grid.shape),
        inventory_grid=grid,
        inventory_values=np.zeros(grid.shape),
    )

    result = proxy.distribute(100.0)

    assert not np.isnan(result).any()
    np.testing.assert_allclose(result, 0.0)
