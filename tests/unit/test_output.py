import numpy as np
import xarray as xr
import pytest

from openmethane_prior.outputs import initialise_output, create_output_dataset, expand_layer_dims

def test_initialise_output(config, input_files, start_date, end_date):
    assert not config.output_domain_file.exists()

    initialise_output(config, start_date, end_date)

    assert config.output_domain_file.exists()

    # Idempotent
    initialise_output(config, start_date, end_date)


def test_create_output_dataset(config, input_files, start_date, end_date):
    domain_ds = config.domain_dataset()

    assert not config.output_domain_file.exists()

    output_ds = create_output_dataset(config, start_date, end_date)

    # validate input domain hasn't changed before we assert about output
    assert domain_ds.sizes["COL"] == 454, "reference domain COL dimension has changed"
    assert domain_ds.sizes["ROW"] == 430, "reference domain ROW dimension has changed"

    # dimensions
    assert output_ds.sizes["x"] == domain_ds.sizes["COL"], "x dimension doesnt match domain"
    assert output_ds.sizes["y"] == domain_ds.sizes["ROW"], "y dimension doesnt match domain"

    # attributes
    assert output_ds.attrs["DX"] == domain_ds.attrs["DX"]
    assert output_ds.attrs["DY"] == 10000
    assert output_ds.attrs["title"] == "Open Methane prior emissions estimate"
    assert isinstance(output_ds.attrs["comment"], str)
    assert isinstance(output_ds.attrs["history"], str)
    assert isinstance(output_ds.attrs["openmethane_prior_version"], str)

    # projection
    assert output_ds["grid_projection"].attrs["grid_mapping_name"] == "lambert_conformal_conic"
    assert output_ds["grid_projection"].attrs["standard_parallel"] == (domain_ds.attrs["TRUELAT1"], domain_ds.attrs["TRUELAT2"])
    assert output_ds["grid_projection"].attrs["longitude_of_central_meridian"] == domain_ds.attrs["STAND_LON"]
    assert output_ds["grid_projection"].attrs["latitude_of_projection_origin"] == domain_ds.attrs["MOAD_CEN_LAT"]

    # bounds
    assert output_ds["time"].values.tolist() == xr.date_range(start=start_date, end=end_date, use_cftime=True).tolist()


def test_expand_layer_dims_errors():
    test_xr = xr.DataArray([1, 2, 3]) # 1-dimensional array

    with pytest.raises(ValueError) as e:
        expand_layer_dims(test_xr)

    assert "minimum of 2 dimensions" in str(e.value)

def test_expand_layer_dims_extra_dims():
    # adds 1-length time and vertical dimensions if not present
    test_xr = xr.DataArray([
        [1, 2, 3],
        [4, 5, 6],
    ])
    expanded = expand_layer_dims(test_xr)

    assert expanded.ndim == 4
    assert expanded.shape == (1, 1, 2, 3)
    assert list(expanded[0][0][0]) == [1, 2, 3]
    assert list(expanded[0][0][1]) == [4, 5, 6]

def test_expand_layer_dims_add_time_dim():
    test_xr = xr.DataArray([
        [1, 2],
        [4, 5],
    ])
    expanded = expand_layer_dims(test_xr, time_steps=3)

    assert expanded.ndim == 4
    assert expanded.shape == (3, 1, 2, 2) # first dimension is time
    # copies the existing data for each time step
    assert list(expanded[0][0][0]) == [1, 2]
    assert list(expanded[0][0][1]) == [4, 5]
    assert list(expanded[1][0][0]) == [1, 2]
    assert list(expanded[1][0][1]) == [4, 5]
    assert list(expanded[2][0][0]) == [1, 2]
    assert list(expanded[2][0][1]) == [4, 5]

def test_expand_layer_dims_add_time_steps():
    test_xr = xr.DataArray([[[
        [1, 2],
        [4, 5],
    ]]])
    # already has correct dims, but not enough time steps
    assert test_xr.ndim == 4
    assert test_xr.shape == (1, 1, 2, 2)

    expanded = expand_layer_dims(test_xr, time_steps=3)

    # time dim filled to 3
    assert expanded.shape == (3, 1, 2, 2)

    # copies the existing data for each time step
    assert list(expanded[0][0][0]) == [1, 2]
    assert list(expanded[0][0][1]) == [4, 5]
    assert list(expanded[1][0][0]) == [1, 2]
    assert list(expanded[1][0][1]) == [4, 5]
    assert list(expanded[2][0][0]) == [1, 2]
    assert list(expanded[2][0][1]) == [4, 5]
