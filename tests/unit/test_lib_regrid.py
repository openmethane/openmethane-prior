import numpy as np
import pytest
import xarray as xr

from openmethane_prior.lib.grid.grid import Grid
from openmethane_prior.lib.utils import load_zipped_pickle
from openmethane_prior.lib.regrid import (
    _compute_cell_edges,
    _compute_from_areas,
    _domain_crop_slices,
    _padded_cell_range,
    regrid_data_array_conservative,
)


# 2×2 domain: 2° cells covering lon 138–142, lat –38 to –34 (eastern Australia)
@pytest.fixture
def domain_grid():
    return Grid(dimensions=(2, 2), origin_xy=(138.0, -38.0), cell_size=(2.0, 2.0))


# 4×4 source at 1° resolution; cells align exactly with domain cell boundaries
@pytest.fixture
def source_da():
    lats = np.array([-37.5, -36.5, -35.5, -34.5])
    lons = np.array([138.5, 139.5, 140.5, 141.5])
    return xr.DataArray(
        np.ones((4, 4), dtype=np.float32),
        dims=["latitude", "longitude"],
        coords={"latitude": lats, "longitude": lons},
    )


def test_2d_output_shape_and_dims(domain_grid, source_da, tmp_path):
    result = regrid_data_array_conservative(source_da, domain_grid, tmp_path, "t2d")
    assert result.shape == domain_grid.shape
    assert result.dims == ("y", "x")


def test_3d_time_coord_preserved(domain_grid, source_da, tmp_path):
    times = np.array(["2022-01-01", "2022-02-01"], dtype="datetime64[ns]")
    da_3d = xr.DataArray(
        np.stack([source_da.values, source_da.values * 2.0]),
        dims=["time", "latitude", "longitude"],
        coords={
            "time": times,
            "latitude": source_da["latitude"],
            "longitude": source_da["longitude"],
        },
    )
    result = regrid_data_array_conservative(da_3d, domain_grid, tmp_path, "t3d")

    assert result.dims == ("time", "y", "x")
    assert result.shape == (2, *domain_grid.shape)
    np.testing.assert_array_equal(result["time"].values, times)
    # second time step should be exactly double the first
    np.testing.assert_allclose(result[1].values, 2.0 * result[0].values, rtol=1e-5)


def test_cache_file_created(domain_grid, source_da, tmp_path):
    assert list(tmp_path.glob("tcache_*_weights.p.gz")) == []
    regrid_data_array_conservative(source_da, domain_grid, tmp_path, "tcache")
    assert len(list(tmp_path.glob("tcache_*_weights.p.gz"))) == 1


def test_cache_hit_gives_identical_result(domain_grid, source_da, tmp_path):
    r1 = regrid_data_array_conservative(source_da, domain_grid, tmp_path, "thit")
    r2 = regrid_data_array_conservative(source_da, domain_grid, tmp_path, "thit")
    np.testing.assert_array_equal(r1.values, r2.values)


def test_nonoverlapping_source_all_zero(domain_grid, tmp_path):
    # source in the tropics — no overlap with the Australian domain
    lats = np.array([10.5, 11.5, 12.5, 13.5])
    lons = np.array([138.5, 139.5, 140.5, 141.5])
    da = xr.DataArray(
        np.ones((4, 4), dtype=np.float32),
        dims=["latitude", "longitude"],
        coords={"latitude": lats, "longitude": lons},
    )

    result = regrid_data_array_conservative(da, domain_grid, tmp_path, "tzero")

    assert (result.values == 0.0).all()


def test_extensive_differs_from_density(domain_grid, source_da, tmp_path):
    r_density = regrid_data_array_conservative(source_da, domain_grid, tmp_path, "text_d")
    r_extensive = regrid_data_array_conservative(source_da, domain_grid, tmp_path, "text_e", extensive=True)

    # source cell areas are ~1e10 m², so extensive normalises values down by that factor
    assert not np.allclose(r_density.values, r_extensive.values)


def test_extensive_normalises_by_source_cell_area(domain_grid, source_da, tmp_path):
    # extensive=True divides by from_areas before regridding; the result should
    # equal the density result divided by the uniform source cell area
    lat_edges = _compute_cell_edges(source_da["latitude"].values)
    lon_edges = _compute_cell_edges(source_da["longitude"].values)
    from_areas = _compute_from_areas(lat_edges, lon_edges)  # (4, 4) array in m²

    r_density = regrid_data_array_conservative(source_da, domain_grid, tmp_path, "tnorm_d")
    # divide each source cell by its area, then regrid
    density_da = source_da / xr.DataArray(
        from_areas,
        dims=["latitude", "longitude"],
        coords=source_da.coords,
    )
    r_manual = regrid_data_array_conservative(density_da, domain_grid, tmp_path, "tnorm_m")
    r_extensive = regrid_data_array_conservative(source_da, domain_grid, tmp_path, "tnorm_e", extensive=True)

    np.testing.assert_allclose(r_extensive.values, r_manual.values, rtol=1e-5)


def test_mass_conservation(domain_grid, source_da, tmp_path):
    # total weighted mass in (source × from_area) ≈ total weighted mass out (result × domain_area)
    lat_edges = _compute_cell_edges(source_da["latitude"].values)
    lon_edges = _compute_cell_edges(source_da["longitude"].values)
    from_areas = _compute_from_areas(lat_edges, lon_edges)
    total_in = float((source_da.values * from_areas).sum())

    result = regrid_data_array_conservative(source_da, domain_grid, tmp_path, "tmass")

    # W divides by domain_grid.cell_area (in deg² for EPSG:4326), so multiplying
    # result back by cell_area gives units of m² — consistent with total_in
    total_out = float((result.values * domain_grid.cell_area).sum())

    np.testing.assert_allclose(total_out, total_in, rtol=0.005)


def test_nan_source_cells_not_propagated(domain_grid, source_da, tmp_path):
    # Domain cell (y=0, x=0) covers lon 138–140, lat –38 to –36 and intersects
    # four 1° source cells. Setting one of them to NaN must not make the domain
    # cell NaN — the remaining three concrete cells should still contribute.
    da_with_nan = source_da.copy(deep=True)
    da_with_nan.values[0, 0] = np.nan  # lat –37.5, lon 138.5

    result = regrid_data_array_conservative(da_with_nan, domain_grid, tmp_path, "tnan")

    assert np.isfinite(result.values[0, 0]), (
        "Domain cell overlapping a NaN source cell must not itself become NaN "
        "when other intersecting source cells have concrete values."
    )

    # Run the same test with a zero in the cell which had np.nan, the results
    # should be identical
    da_with_zero = source_da.copy(deep=True)
    da_with_zero.values[0, 0] = 0  # same coords as da_with_nan nan value

    result_clean = regrid_data_array_conservative(da_with_zero, domain_grid, tmp_path, "tnan_clean")

    np.testing.assert_array_equal(result, result_clean)


def test_cell_edges_hundredth_degree_grid():
    # edges of 0.01 degree cells fall on the third decimal place, and must not
    # be rounded onto the cell centres
    centres = np.array([113.40, 113.41, 113.42])

    result = _compute_cell_edges(centres)

    np.testing.assert_allclose(result, [113.395, 113.405, 113.415, 113.425])


def test_source_beyond_domain_gives_same_result(domain_grid, source_da, tmp_path):
    # 1° source over lon 130 to 150, lat -45 to -25, matching source_da inside the
    # domain and with large values outside it
    lats = np.arange(-44.5, -25.0, 1.0)
    lons = np.arange(130.5, 150.0, 1.0)
    large_da = xr.DataArray(
        np.full((len(lats), len(lons)), 1000.0, dtype=np.float32),
        dims=["latitude", "longitude"],
        coords={"latitude": lats, "longitude": lons},
    )
    large_da.loc[{"latitude": slice(-38, -34), "longitude": slice(138, 142)}] = 1.0

    r_large = regrid_data_array_conservative(large_da, domain_grid, tmp_path, "tlarge")
    r_small = regrid_data_array_conservative(source_da, domain_grid, tmp_path, "tsmall")

    np.testing.assert_allclose(r_large.values, r_small.values, rtol=1e-6)


def test_weights_cover_only_cropped_source(domain_grid, tmp_path):
    # 1° source over lon 100 to 160, lat -50 to 0, much larger than the domain
    lats = np.arange(-49.5, 0.0, 1.0)
    lons = np.arange(100.5, 160.0, 1.0)
    large_da = xr.DataArray(
        np.ones((len(lats), len(lons)), dtype=np.float32),
        dims=["latitude", "longitude"],
        coords={"latitude": lats, "longitude": lons},
    )

    regrid_data_array_conservative(large_da, domain_grid, tmp_path, "tcrop")

    (weights_file,) = tmp_path.glob("tcrop_*_weights.p.gz")
    weights = load_zipped_pickle(weights_file)
    # the 4x4 cells under the domain, the cells starting on its upper edges,
    # and one cell of padding either side: 7x7 of the source's 50x60 cells
    assert weights.shape == (4, 7 * 7)


def test_weights_not_reused_for_different_source_grid(domain_grid, source_da, tmp_path):
    # same cache_name, but a 0.5° source grid instead of 1°
    lats = np.arange(-37.75, -34.0, 0.5)
    lons = np.arange(138.25, 142.0, 0.5)
    fine_da = xr.DataArray(
        np.ones((len(lats), len(lons)), dtype=np.float32),
        dims=["latitude", "longitude"],
        coords={"latitude": lats, "longitude": lons},
    )
    regrid_data_array_conservative(source_da, domain_grid, tmp_path, "tshared")

    r_shared = regrid_data_array_conservative(fine_da, domain_grid, tmp_path, "tshared")
    r_fresh = regrid_data_array_conservative(fine_da, domain_grid, tmp_path, "tfresh")

    np.testing.assert_array_equal(r_shared.values, r_fresh.values)
    assert len(list(tmp_path.glob("tshared_*_weights.p.gz"))) == 2


def test_padded_cell_range_pads_one_cell():
    edges = np.arange(0.0, 11.0)  # 10 cells of width 1

    result = _padded_cell_range(edges, 3.5, 5.5)

    # cells 3 to 5 contain the range, padded to 2 to 6
    assert result == slice(2, 7)


def test_padded_cell_range_clamped_to_grid():
    edges = np.arange(0.0, 11.0)

    result = _padded_cell_range(edges, -5.0, 20.0)

    assert result == slice(0, 10)


def test_padded_cell_range_outside_grid_not_empty():
    edges = np.arange(0.0, 11.0)

    result = _padded_cell_range(edges, 20.0, 25.0)

    assert result == slice(9, 10)


def test_domain_crop_slices_lambert_domain():
    # Lambert conformal domain over south-east Australia; its edges curve in
    # lon/lat, so the crop must cover the corners of every cell
    domain_grid = Grid(
        dimensions=(10, 10),
        origin_xy=(-500000.0, -500000.0),
        cell_size=(100000.0, 100000.0),
        proj_params="+proj=lcc +lat_1=-30 +lat_2=-40 +lat_0=-35 +lon_0=145 +ellps=WGS84",
    )
    lat_edges = np.arange(-60.0, 0.5, 0.5)
    lon_edges = np.arange(100.0, 180.5, 0.5)
    cell_bounds_lon, cell_bounds_lat = domain_grid.cell_bounds_lonlat()

    lat_slice, lon_slice = _domain_crop_slices(domain_grid, lat_edges, lon_edges)

    # every domain cell corner lies inside the cropped region, at least one
    # padding cell from its edge
    assert lat_edges[lat_slice.start + 1] <= cell_bounds_lat.min()
    assert lat_edges[lat_slice.stop - 1] >= cell_bounds_lat.max()
    assert lon_edges[lon_slice.start + 1] <= cell_bounds_lon.min()
    assert lon_edges[lon_slice.stop - 1] >= cell_bounds_lon.max()
    # and the region is much smaller than the source grid
    assert lat_slice.stop - lat_slice.start < 30
    assert lon_slice.stop - lon_slice.start < 40


def test_domain_crop_slices_antimeridian_not_cropped():
    domain_grid = Grid(
        dimensions=(4, 4),
        origin_xy=(-200000.0, -200000.0),
        cell_size=(100000.0, 100000.0),
        proj_params="+proj=lcc +lat_1=-30 +lat_2=-50 +lat_0=-40 +lon_0=180 +ellps=WGS84",
    )
    lat_edges = np.arange(-90.0, 91.0)
    lon_edges = np.arange(-180.0, 181.0)

    result = _domain_crop_slices(domain_grid, lat_edges, lon_edges)

    assert result == (slice(0, 180), slice(0, 360))
