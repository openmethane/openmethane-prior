import numpy as np
import xarray as xr
import pytest

from openmethane_prior.outputs import create_output_dataset, expand_sector_dims, write_output_dataset, add_sector
from openmethane_prior.sector.sector import SectorMeta


def test_write_output_dataset(config, input_files):
    output_ds = create_output_dataset(config)

    assert not config.output_file.exists()

    write_output_dataset(config, output_ds)

    assert config.output_file.exists()


def test_create_output_dataset(config, input_files):
    domain_ds = config.domain_dataset()

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
    # adds 1-length time and vertical dimensions if not present
    test_xr = xr.DataArray([
        [1, 2, 3],
        [4, 5, 6],
    ])
    expanded = expand_sector_dims(test_xr)

    assert expanded.ndim == 4
    assert expanded.shape == (1, 1, 2, 3)
    assert list(expanded[0][0][0]) == [1, 2, 3]
    assert list(expanded[0][0][1]) == [4, 5, 6]

def test_expand_sector_dims_add_time_dim():
    test_xr = xr.DataArray([
        [1, 2],
        [4, 5],
    ])
    expanded = expand_sector_dims(test_xr, time_steps=3)

    assert expanded.ndim == 4
    assert expanded.shape == (3, 1, 2, 2) # first dimension is time
    # copies the existing data for each time step
    assert list(expanded[0][0][0]) == [1, 2]
    assert list(expanded[0][0][1]) == [4, 5]
    assert list(expanded[1][0][0]) == [1, 2]
    assert list(expanded[1][0][1]) == [4, 5]
    assert list(expanded[2][0][0]) == [1, 2]
    assert list(expanded[2][0][1]) == [4, 5]

def test_expand_sector_dims_add_time_steps():
    test_xr = xr.DataArray([[[
        [1, 2],
        [4, 5],
    ]]])
    # already has correct dims, but not enough time steps
    assert test_xr.ndim == 4
    assert test_xr.shape == (1, 1, 2, 2)

    expanded = expand_sector_dims(test_xr, time_steps=3)

    # time dim filled to 3
    assert expanded.shape == (3, 1, 2, 2)

    # copies the existing data for each time step
    assert list(expanded[0][0][0]) == [1, 2]
    assert list(expanded[0][0][1]) == [4, 5]
    assert list(expanded[1][0][0]) == [1, 2]
    assert list(expanded[1][0][1]) == [4, 5]
    assert list(expanded[2][0][0]) == [1, 2]
    assert list(expanded[2][0][1]) == [4, 5]

def test_add_sector_defaults(config, input_files):
    test_ds = create_output_dataset(config)

    sector_meta = SectorMeta(
        name="test_sector",
    )
    sector_shape = (test_ds.sizes["time"], 1, config.domain_grid().shape[0], config.domain_grid().shape[1])
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
    assert test_ds[sector_var].attrs["units"] == "kg/m2/s"
    assert test_ds[sector_var].attrs["grid_mapping"] == test_ds["land_mask"].attrs["grid_mapping"]


def test_add_sector_meta(config, input_files):
    test_ds = create_output_dataset(config)

    sector_meta = SectorMeta(
        name="test_sector",
        cf_standard_name="standard_name_suffix",
        cf_long_name="test long name",
    )
    sector_shape = (test_ds.sizes["time"], 1, config.domain_grid().shape[0], config.domain_grid().shape[1])
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
    assert test_ds[sector_var].attrs["units"] == "kg/m2/s"
    assert test_ds[sector_var].attrs["grid_mapping"] == test_ds["land_mask"].attrs["grid_mapping"]
