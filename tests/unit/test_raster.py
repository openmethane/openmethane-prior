import numpy as np
import rioxarray as rxr
import xarray as xr

from openmethane_prior.grid.grid import Grid
from openmethane_prior.raster import remap_raster

def test_remap_raster(config, input_files):
    test_coord = (2500, 3000) # let's read this in later
    distance_tolerance = 1e4 # allowed mismatch between initial and final coords in metres
    epsilon = 1e-5 # small number
    def maxloc(a): return np.unravel_index(a.argmax(), a.shape)

    domain_dataset = config.inventory_dataset()
    domain_grid = config.inventory_grid()

    lat = domain_dataset['lat']
    lon = domain_dataset['lon']

    ntl_raw = rxr.open_rasterio(
        config.as_input_file(config.layer_inputs.ntl_path), masked=True
    )
    # filter nans
    np.nan_to_num(ntl_raw, copy=False)
    ntl = ntl_raw.sum(axis=0)
    # now reconstruct with one nonzero point
    ntl *= 0.
    ntl[test_coord] = 1.
    # now clip to remove offshore lights
    om_ntl = remap_raster(ntl, domain_grid, AREA_OR_POINT = ntl_raw.AREA_OR_POINT)

    # now a few tests on outputs
    # only one nonzero point in output
    assert (om_ntl > epsilon).sum() == 1, f"{(om_ntl > epsilon).sum()} nonzero output points, should be 1"

    input_loc = np.array([
        float(ntl_raw.y[test_coord[0]]),
        float(ntl_raw.x[test_coord[1]])
    ])
    output_loc = np.array([
        lat[maxloc(om_ntl)],
        lon[maxloc(om_ntl)]
    ])

    np.testing.assert_allclose(output_loc, input_loc, atol=distance_tolerance)

def test_remap_raster_area():
    # target is a regular 4x4 grid from -4,-4 to 4,4
    target_grid = Grid(
        dimensions=(4, 4),
        origin_xy=(-4, -4),
        cell_size=(2, 2),
    )
    # create a regular 16x16 grid from -8.25,-8.25 to 7.75,7.75
    # the 0.25 offset is so that it doesn't align with the target grid
    test_input = xr.DataArray(
        coords={ "y": np.arange(-8.0, 8.0) - 0.25, "x": np.arange(-8.0, 8.0) - 0.25 },
        data=np.zeros((16, 16)),
    )
    test_input[6, 6] = 1.0 # add a single value at -2.25, -2.25

    # 'Point' means the coord represents the center point of the cell
    # -2.25,-2.25 should fall into the cell at 0,0
    result = remap_raster(test_input, target_grid, AREA_OR_POINT='Point')
    assert result[0, 0] == 1.0
    assert result[1, 1] == 0.0 # test the negative

    # 'Area' means the coord represents the llc point of the cell
    # -2.25,-2.25 should be shifted to -1.75, -1.75, falling into 1,1
    result = remap_raster(test_input, target_grid, AREA_OR_POINT='Area')
    assert result[0, 0] == 0.0
    assert result[1, 1] == 1.0 # now falls in 1,1


def test_remap_raster_input_projection():
    test_point = (144.9631, -37.8136) # Melbourne, Australia

    target_grid = Grid(
        dimensions=(80, 80),
        origin_xy=(-40, -40),
        cell_size=(10, 10), # cell size of 10 degrees
        proj_params="EPSG:7843", # GDA2020 in lon/lat
    )
    target_x, target_y, _ = target_grid.lonlat_to_cell_index(test_point[0], test_point[1])

    # use a Grid to help us define a source dataset in a different projection
    source_grid = Grid(
        dimensions=(1000, 1000),
        origin_xy=(-50000000, -50000000),
        cell_size=(100000, 100000), # cell size of 100km
        proj_params="EPSG:7845", # GDA2020 in meters
    )
    test_input = xr.DataArray(
        coords={ "y": source_grid.cell_coords_y(), "x": source_grid.cell_coords_x() },
        data=np.zeros(source_grid.shape),
    )
    source_x, source_y, _ = source_grid.lonlat_to_cell_index(test_point[0], test_point[1])

    # add a single value in the cell at -144.9631,-37.8136
    test_input[source_y, source_x] = 1.0

    # remap to the target grid
    result = remap_raster(test_input, target_grid, input_crs=source_grid.projection.crs)

    # check that our single value occurs in the right target cell
    assert result[target_y, target_x] == 1.0
