import numpy as np
import rioxarray as rxr
import xarray as xr

from openmethane_prior.data_sources.inventory import inventory_domain_data_source
from openmethane_prior.data_sources.nightlights import night_lights_data_source
from openmethane_prior.lib.grid.grid import Grid
from openmethane_prior.lib import raster
from openmethane_prior.lib.raster import remap_raster


def test_remap_raster(config, input_files, data_manager, data_manager_fetch_only):
    test_coord = (2500, 3000)  # let's read this in later
    distance_tolerance = 1e4  # allowed mismatch between initial and final coords in metres
    epsilon = 1e-5  # small number

    def maxloc(a):
        return np.unravel_index(a.argmax(), a.shape)

    inventory_domain = data_manager.get_asset(inventory_domain_data_source).data
    domain_dataset = inventory_domain.dataset
    domain_grid = inventory_domain.grid

    lat = domain_dataset["lat"]
    lon = domain_dataset["lon"]

    # avoid calling night_lights parse() since we won't use parsed data
    night_lights_asset = data_manager_fetch_only.get_asset(night_lights_data_source)
    ntl_raw = rxr.open_rasterio(night_lights_asset.path, masked=True)

    # filter nans
    np.nan_to_num(ntl_raw, copy=False)
    ntl = ntl_raw.sum(axis=0)
    # now reconstruct with one nonzero point
    ntl *= 0.0
    ntl[test_coord] = 1.0
    # now clip to remove offshore lights
    om_ntl = remap_raster(ntl, domain_grid)

    # now a few tests on outputs
    # only one nonzero point in output
    assert (
        om_ntl > epsilon
    ).sum() == 1, f"{(om_ntl > epsilon).sum()} nonzero output points, should be 1"

    input_loc = np.array([float(ntl_raw.y[test_coord[0]]), float(ntl_raw.x[test_coord[1]])])
    output_loc = np.array([lat[maxloc(om_ntl)], lon[maxloc(om_ntl)]])

    np.testing.assert_allclose(output_loc, input_loc, atol=distance_tolerance)


def test_remap_raster_input_projection():
    test_point = (144.9631, -37.8136)  # Melbourne, Australia

    target_grid = Grid(
        dimensions=(20, 20),
        origin_xy=(130.5, -45.5),
        cell_size=(1, 1),  # cell size of 1 degrees (roughly 100km)
        proj_params="EPSG:7843",  # GDA2020 in lon/lat
    )
    target_x, target_y, _ = target_grid.lonlat_to_cell_index(test_point[0], test_point[1])

    # use a Grid to help us define a source dataset in a different projection
    source_grid = Grid(
        dimensions=(900, 600),
        origin_xy=(-4564775.59, -7428980.66),
        cell_size=(10000, 10000),  # cell size of 10km
        proj_params="EPSG:7845",  # GDA2020 in meters
    )
    test_input = xr.DataArray(
        coords={"y": source_grid.cell_coords_y(), "x": source_grid.cell_coords_x()},
        data=np.zeros(source_grid.shape),
    )
    source_x, source_y, _ = source_grid.lonlat_to_cell_index(test_point[0], test_point[1])

    # add a single value in the cell at -144.9631,-37.8136
    test_input[source_y, source_x] = 1.0

    # remap to the target grid
    result = remap_raster(test_input, target_grid, input_crs=source_grid.projection.crs)

    # check that our single value occurs in the right target cell
    assert result[target_y, target_x] == 1.0


def test_remap_raster_bool_input_cropped_to_target():
    target_grid = Grid(
        dimensions=(10, 10),
        origin_xy=(130.0, -40.0),
        cell_size=(1, 1),
        proj_params="EPSG:4326",
    )
    # a bool raster extending well beyond the target, with y descending as
    # in a GeoTIFF
    test_input = xr.DataArray(
        coords={"y": np.arange(-10.125, -60.0, -0.25), "x": np.arange(110.125, 170.0, 0.25)},
        data=np.zeros((200, 240), dtype=bool),
    )
    inside_point = (135.125, -35.125)
    outside_point = (120.125, -35.125)
    test_input.loc[{"x": inside_point[0], "y": inside_point[1]}] = True
    test_input.loc[{"x": outside_point[0], "y": outside_point[1]}] = True
    target_x, target_y, _ = target_grid.lonlat_to_cell_index(*inside_point)

    result = remap_raster(test_input, target_grid)

    assert result.shape == target_grid.shape
    assert result.sum() == 1
    assert result[target_y, target_x] == 1


def test_remap_raster_input_outside_target():
    target_grid = Grid(
        dimensions=(10, 10),
        origin_xy=(130.0, -40.0),
        cell_size=(1, 1),
        proj_params="EPSG:4326",
    )
    test_input = xr.DataArray(
        coords={"y": np.arange(-10.5, -20.0, -1.0), "x": np.arange(100.5, 110.0, 1.0)},
        data=np.ones((10, 10), dtype=bool),
    )

    result = remap_raster(test_input, target_grid)

    assert result.shape == target_grid.shape
    assert result.sum() == 0


def test_remap_raster_sums_values_across_row_blocks(monkeypatch):
    # process a few rows at a time, so the input spans several blocks
    monkeypatch.setattr(raster, "_BLOCK_CELLS", 100)
    target_grid = Grid(
        dimensions=(10, 10),
        origin_xy=(130.0, -40.0),
        cell_size=(1, 1),
        proj_params="EPSG:4326",
    )
    # four input cells in each target cell
    test_input = xr.DataArray(
        coords={"y": np.arange(-30.25, -40.0, -0.5), "x": np.arange(130.25, 140.0, 0.5)},
        data=np.zeros((20, 20)),
    )
    test_input.loc[{"x": 135.25, "y": -35.25}] = 2.5
    test_input.loc[{"x": 135.75, "y": -35.75}] = -1.0
    test_input.loc[{"x": 131.25, "y": -38.75}] = 4.0
    first_x, first_y, _ = target_grid.lonlat_to_cell_index(135.5, -35.5)
    second_x, second_y, _ = target_grid.lonlat_to_cell_index(131.5, -38.5)

    result = remap_raster(test_input, target_grid)

    assert result[first_y, first_x] == 1.5
    assert result[second_y, second_x] == 4.0
    assert result.sum() == 5.5


def test_remap_raster_nan_input():
    target_grid = Grid(
        dimensions=(10, 10),
        origin_xy=(130.0, -40.0),
        cell_size=(1, 1),
        proj_params="EPSG:4326",
    )
    test_input = xr.DataArray(
        coords={"y": np.arange(-30.25, -40.0, -0.5), "x": np.arange(130.25, 140.0, 0.5)},
        data=np.zeros((20, 20)),
    )
    # a NaN and a finite value in the same target cell
    test_input.loc[{"x": 135.25, "y": -35.25}] = np.nan
    test_input.loc[{"x": 135.75, "y": -35.75}] = 1.0
    test_input.loc[{"x": 131.25, "y": -38.75}] = 4.0
    nan_x, nan_y, _ = target_grid.lonlat_to_cell_index(135.5, -35.5)
    other_x, other_y, _ = target_grid.lonlat_to_cell_index(131.5, -38.5)

    result = remap_raster(test_input, target_grid)

    assert np.isnan(result[nan_y, nan_x])
    assert np.isnan(result).sum() == 1
    assert result[other_y, other_x] == 4.0


def test_remap_raster_x_y_dimension_order():
    target_grid = Grid(
        dimensions=(10, 10),
        origin_xy=(130.0, -40.0),
        cell_size=(1, 1),
        proj_params="EPSG:4326",
    )
    # dimensions ordered (x, y) rather than the usual (y, x), with a
    # non-square crop
    test_input = xr.DataArray(
        coords={"x": np.arange(130.25, 140.0, 0.5), "y": np.arange(-35.25, -40.0, -0.5)},
        data=np.zeros((20, 10)),
    )
    test_input.loc[{"x": 135.25, "y": -38.75}] = 3.0
    target_x, target_y, _ = target_grid.lonlat_to_cell_index(135.5, -38.5)

    result = remap_raster(test_input, target_grid)

    assert result[target_y, target_x] == 3.0
    assert result.sum() == 3.0


def test_remap_raster_includes_input_beyond_target_corners():
    # in a southern-hemisphere Lambert conformal grid, the middle of the
    # bottom edge lies further south than the bottom corners
    target_grid = Grid(
        dimensions=(40, 10),
        origin_xy=(-1000000.0, -1500000.0),
        cell_size=(50000, 50000),
        proj_params="+proj=lcc +lat_1=-15 +lat_2=-40 +lat_0=-25 +lon_0=133 +ellps=WGS84",
    )
    test_input = xr.DataArray(
        coords={"y": np.arange(-10.05, -50.0, -0.1), "x": np.arange(110.05, 160.0, 0.1)},
        data=np.zeros((400, 500)),
    )
    # an input cell under the bottom-centre target cell, south of every corner
    bottom_centre_lon, bottom_centre_lat = target_grid.xy_to_lonlat(0.0, -1475000.0)
    _, corner_lats = target_grid.xy_to_lonlat(
        np.array([-1000000.0, 1000000.0]), np.array([-1500000.0, -1500000.0])
    )
    input_cell = test_input.sel(x=bottom_centre_lon, y=bottom_centre_lat, method="nearest")
    assert input_cell.y < corner_lats.min()
    test_input.loc[{"x": input_cell.x, "y": input_cell.y}] = 1.0
    target_x, target_y, _ = target_grid.lonlat_to_cell_index(input_cell.x, input_cell.y)

    result = remap_raster(test_input, target_grid)

    assert target_y == 0
    assert result[target_y, target_x] == 1.0
