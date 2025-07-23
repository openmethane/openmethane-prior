import numpy as np
import rioxarray as rxr

from openmethane_prior.raster import remap_raster

def test_remap_raster(config, input_files):
    test_coord = (2500, 3000) # let's read this in later
    distance_tolerance = 1e4 # allowed mismatch between initial and final coords in metres
    epsilon = 1e-5 # small number
    def maxloc(a): return np.unravel_index(a.argmax(), a.shape)

    lat = config.domain_dataset()['LAT'][...].squeeze()
    lon = config.domain_dataset()['LON'][...].squeeze()

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
    om_ntl = remap_raster(ntl, config.domain_grid(), AREA_OR_POINT = ntl_raw.AREA_OR_POINT)

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
