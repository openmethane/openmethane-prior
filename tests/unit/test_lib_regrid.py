import numpy as np
import pytest
import xarray as xr

from openmethane_prior.lib.grid.grid import Grid
from openmethane_prior.lib.regrid import _compute_cell_edges, _compute_from_areas, regrid_data_array_conservative


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
    assert not (tmp_path / "tcache_weights.p.gz").exists()
    regrid_data_array_conservative(source_da, domain_grid, tmp_path, "tcache")
    assert (tmp_path / "tcache_weights.p.gz").exists()


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
