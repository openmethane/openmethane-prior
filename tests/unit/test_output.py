import numpy as np
import xarray as xr
import pytest

from openmethane_prior.lib.outputs import (
    COORD_NAMES,
    add_ch4_total,
    add_sector,
    create_output_dataset,
    emission_encoding,
    expand_sector_dims,
)
from openmethane_prior.lib.sector.sector import PriorSector


def create_mock_prior_sector(**kwargs) -> PriorSector:
    """Return a minimal PriorSector for use in tests, with overridable fields."""
    defaults = dict(
        name="test_sector",
        emission_category="natural",
        create_estimate=lambda a, b, c: None,
    )
    return PriorSector(**(defaults | kwargs))


def test_create_output_dataset(config, input_files):
    domain_ds = config.domain().dataset

    assert not config.output_file.exists()

    output_ds = create_output_dataset(config)

    # validate input domain hasn't changed before we assert about output
    assert domain_ds.sizes["x"] == 10, "reference domain x dimension has changed"
    assert domain_ds.sizes["y"] == 10, "reference domain y dimension has changed"

    # dimensions
    assert output_ds.sizes["x"] == domain_ds.sizes["x"], "x dimension doesnt match domain"
    assert output_ds.sizes["y"] == domain_ds.sizes["y"], "y dimension doesnt match domain"

    # attributes
    assert output_ds.attrs["DX"] == domain_ds.attrs["DX"]
    assert output_ds.attrs["DY"] == domain_ds.attrs["DY"]
    assert output_ds.attrs["title"] == "Open Methane prior emissions estimate"
    assert output_ds.attrs["Conventions"] == "CF-1.12"
    assert isinstance(output_ds.attrs["comment"], str)
    assert isinstance(output_ds.attrs["history"], str)
    assert isinstance(output_ds.attrs["openmethane_prior_version"], str)

    assert output_ds.attrs["domain_name"] == "au-test"
    assert output_ds.attrs["domain_version"] == "v1"
    assert output_ds.attrs["domain_slug"] == "test"

    # projection
    assert output_ds["lambert_conformal"].attrs == domain_ds["lambert_conformal"].attrs

    # bounds
    assert output_ds["time"].size == (config.end_date - config.start_date).days + 1 # one time step per day, end inclusive
    assert output_ds["time"].values[0] == np.datetime64(config.start_date)
    assert output_ds["time"].values[-1] == np.datetime64(config.end_date)

    assert output_ds["x"].attrs["bounds"] == "x_bounds"
    assert output_ds["x_bounds"].shape == (output_ds["x"].size, 2)
    assert output_ds["y"].attrs["bounds"] == "y_bounds"
    assert output_ds["y_bounds"].shape == (output_ds["y"].size, 2)

    # grid cell names
    assert str(output_ds["cell_name"][0, 0].data) == "test.0.0"
    assert str(output_ds["cell_name"][0, 2].data) == "test.2.0"
    assert str(output_ds["cell_name"][2, 0].data) == "test.0.2"
    assert str(output_ds["cell_name"][9, 9].data) == "test.9.9"

    # ensure georeferenced variables include grid_mapping attribute
    for var_name in output_ds.data_vars.keys():
        # variables that do not need grid_mapping are excluded from this check
        if var_name in ["lat", "lon", "cell_name", "land_mask", "LANDMASK"]:
            continue

        if "x" in output_ds[var_name].coords and "y"  in output_ds[var_name].coords:
            assert "grid_mapping" in output_ds[var_name].attrs, f"Georeferenced variable '{var_name}' is missing grid_mapping"


def test_expand_sector_dims_errors():
    test_xr = xr.DataArray([1, 2, 3]) # 1-dimensional array

    with pytest.raises(ValueError) as e:
        expand_sector_dims(test_xr)

    assert "minimum of 2 dimensions" in str(e.value)

def test_expand_sector_dims_extra_dims():
    # adds a 1-length vertical dimension if not present
    test_xr = xr.DataArray([
        [1, 2, 3],
        [4, 5, 6],
    ])
    expanded = expand_sector_dims(test_xr)

    assert expanded.ndim == 3
    assert expanded.shape == (1, 2, 3)
    assert list(expanded[0][0]) == [1, 2, 3]
    assert list(expanded[0][1]) == [4, 5, 6]


def test_expand_sector_dims_keeps_vertical_dim():
    # data which already has a vertical dimension is left alone
    test_xr = xr.DataArray([[
        [1, 2],
        [4, 5],
    ]])
    expanded = expand_sector_dims(test_xr)

    assert expanded.shape == (1, 2, 2)


def test_expand_sector_dims_rejects_time_dim():
    """Time expansion is no longer performed here, so 4-dimensional data is an error."""
    test_xr = xr.DataArray(np.zeros((3, 1, 2, 2)))

    with pytest.raises(ValueError) as e:
        expand_sector_dims(test_xr)

    assert "maximum of 3 dimensions" in str(e.value)



def test_add_sector_defaults(config, input_files):
    test_ds = create_output_dataset(config)

    sector_meta = create_mock_prior_sector()
    sector_shape = (test_ds.sizes["time"], 1, config.domain().grid.shape[0], config.domain().grid.shape[1])
    sector_data = np.zeros(sector_shape)

    assert sector_meta.name not in test_ds

    add_sector(
        prior_ds=test_ds,
        sector_data=sector_data,
        sector_meta=sector_meta,
    )

    sector_var = f"ch4_sector_{sector_meta.name}"

    assert sector_var in test_ds
    assert test_ds[sector_var].shape == sector_shape

    assert test_ds[sector_var].attrs["standard_name"] == "surface_upward_mass_flux_of_methane"
    assert test_ds[sector_var].attrs["long_name"] == "expected flux of methane caused by sector: test_sector"
    assert test_ds[sector_var].attrs["emission_category"] == "natural"
    assert test_ds[sector_var].attrs["units"] == "kg/m2/s"
    assert test_ds[sector_var].attrs["grid_mapping"] == test_ds["land_mask"].attrs["grid_mapping"]


def test_add_sector_meta(config, input_files):
    test_ds = create_output_dataset(config)

    sector_meta = create_mock_prior_sector(
        emission_category="anthropogenic",
        unfccc_categories=["1.A"],
        cf_standard_name="standard_name_suffix",
        cf_long_name="test long name",
    )
    sector_shape = (test_ds.sizes["time"], 1, config.domain().grid.shape[0], config.domain().grid.shape[1])
    sector_data = np.zeros(sector_shape)

    assert sector_meta.name not in test_ds

    add_sector(
        prior_ds=test_ds,
        sector_data=sector_data,
        sector_meta=sector_meta,
    )

    sector_var = f"ch4_sector_{sector_meta.name}"

    assert sector_var in test_ds
    assert test_ds[sector_var].shape == sector_shape

    assert test_ds[sector_var].attrs["standard_name"] == \
           "surface_upward_mass_flux_of_methane_due_to_emission_from_standard_name_suffix"
    assert test_ds[sector_var].attrs["long_name"] == "test long name"
    assert test_ds[sector_var].attrs["emission_category"] == "anthropogenic"
    assert test_ds[sector_var].attrs["units"] == "kg/m2/s"
    assert test_ds[sector_var].attrs["grid_mapping"] == test_ds["land_mask"].attrs["grid_mapping"]


def test_add_sector_masked_dataarray(config, input_files):
    """A DataArray created from a masked array should have masked cells stored as zero, not NaN."""
    test_ds = create_output_dataset(config)

    sector_meta = create_mock_prior_sector()
    grid_y, grid_x = config.domain().grid.shape

    raw = np.ones((grid_y, grid_x))
    mask = np.zeros((grid_y, grid_x), dtype=bool)
    mask[0, 0] = True  # mask the top-left cell
    # xarray converts masked values to NaN internally; add_sector must then replace them with zero
    sector_data = xr.DataArray(data=np.ma.MaskedArray(raw, mask=mask), dims=["y", "x"])

    add_sector(prior_ds=test_ds, sector_data=sector_data, sector_meta=sector_meta)

    sector_var = f"ch4_sector_{sector_meta.name}"
    result = test_ds[sector_var]

    assert not isinstance(result.values, np.ma.MaskedArray), "output must not be a masked array"
    assert not np.isnan(result.values).any(), "output must not contain NaN values"
    assert result.dims == ("vertical", "y", "x"), "a 2-dimensional sector has no time dim"
    assert (result.values[:, 0, 0] == 0.0).all(), "masked cells must be replaced with zero"
    assert (result.values[:, 0, 1] == 1.0).all(), "unmasked cells must retain their value"


def test_add_sector_nan_values(config, input_files):
    """NaN values in sector data should be replaced with zero in the output."""
    test_ds = create_output_dataset(config)

    sector_meta = create_mock_prior_sector()
    grid_y, grid_x = config.domain().grid.shape

    raw = np.ones((grid_y, grid_x))
    raw[0, 0] = np.nan  # inject NaN into the top-left cell
    sector_data = xr.DataArray(data=raw, dims=["y", "x"])

    add_sector(prior_ds=test_ds, sector_data=sector_data, sector_meta=sector_meta)

    sector_var = f"ch4_sector_{sector_meta.name}"
    result = test_ds[sector_var]

    assert not np.isnan(result.values).any(), "output must not contain NaN values"
    assert (result.values[:, 0, 0] == 0.0).all(), "NaN cells must be replaced with zero"
    assert (result.values[:, 0, 1] == 1.0).all(), "non-NaN cells must retain their value"


def test_emission_encoding_chunks_all_time_steps_together():
    """Emissions chunks must span the full time extent so repeated steps compress."""
    encoding = emission_encoding((31, 1, 430, 454))

    assert encoding["zlib"] is True
    # complevel must be explicit: sector data inheriting complevel 0 from an
    # input file would be written uncompressed
    assert encoding["complevel"] == 4
    assert encoding["shuffle"] is True
    # domain vars copied from the domain file arrive with contiguous storage,
    # which cannot be combined with compression
    assert encoding["contiguous"] is False
    assert encoding["chunksizes"] == (31, 1, 64, 64)


def test_emission_encoding_clamps_chunks_to_small_grids():
    """netCDF rejects chunks larger than the dimension, so small domains clamp."""
    encoding = emission_encoding((3, 1, 10, 12))

    assert encoding["chunksizes"] == (3, 1, 10, 12)


def test_add_sector_compresses_across_time(config, input_files, tmp_path):
    """Sector data written to disk should be compressed and chunked across time."""
    test_ds = create_output_dataset(config)
    grid_y, grid_x = config.domain().grid.shape
    time_steps = test_ds.sizes["time"]

    sector_meta = create_mock_prior_sector()
    # supply an estimate per time step, so the layer keeps its time dimension
    add_sector(
        prior_ds=test_ds,
        sector_data=np.zeros((time_steps, 1, grid_y, grid_x)),
        sector_meta=sector_meta,
    )
    sector_var = f"ch4_sector_{sector_meta.name}"

    assert test_ds[sector_var].encoding["zlib"] is True
    assert test_ds[sector_var].encoding["chunksizes"] == (
        time_steps,
        1,
        min(64, grid_y),
        min(64, grid_x),
    )

    # confirm the encoding survives a write, and values are unchanged
    output_file = tmp_path / "chunked.nc"
    test_ds.to_netcdf(output_file)

    with xr.open_dataset(output_file) as written_ds:
        chunks = written_ds[sector_var].encoding["chunksizes"]
        assert chunks[0] == time_steps, "all time steps should share a chunk"
        assert np.array_equal(written_ds[sector_var].values, test_ds[sector_var].values)


def test_add_ch4_total_compresses_across_time(config, input_files):
    """The total layer should get the same chunking as the sector layers."""
    test_ds = create_output_dataset(config)
    grid_y, grid_x = config.domain().grid.shape

    add_sector(
        prior_ds=test_ds,
        sector_data=np.zeros((grid_y, grid_x)),
        sector_meta=create_mock_prior_sector(),
    )
    add_ch4_total(test_ds)

    assert test_ds["ch4_total"].dims == tuple(COORD_NAMES)

    assert test_ds["ch4_total"].encoding["zlib"] is True
    assert test_ds["ch4_total"].encoding["chunksizes"] == (
        test_ds.sizes["time"],
        1,
        min(64, grid_y),
        min(64, grid_x),
    )


def test_grid_metadata_is_compressed(config, input_files, tmp_path):
    """Grid metadata copied from the domain should be compressed on write."""
    test_ds = create_output_dataset(config)

    for var_name in ["lat", "lon", "land_mask", "LANDMASK"]:
        encoding = test_ds[var_name].encoding
        assert encoding["zlib"] is True, f"{var_name} should be compressed"
        # the domain file supplies complevel 0, which compresses nothing
        assert encoding["complevel"] == 4, f"{var_name} needs an explicit complevel"
        assert encoding["contiguous"] is False, f"{var_name} cannot stay contiguous"

    # land_mask is a 0/1 mask, so it is narrowed on disk
    assert test_ds["land_mask"].encoding["dtype"] == "int8"

    # values must survive the narrowing
    output_file = tmp_path / "metadata.nc"
    test_ds.to_netcdf(output_file)

    with xr.open_dataset(output_file) as written_ds:
        assert written_ds["land_mask"].dtype == np.int8
        assert np.array_equal(written_ds["land_mask"].values, test_ds["land_mask"].values)
        assert np.array_equal(written_ds["lat"].values, test_ds["lat"].values)
