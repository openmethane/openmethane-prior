import numpy as np
import pytest

from openmethane_prior.outputs import initialise_output, create_output_dataset

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
    assert output_ds["time"].values == np.datetime64(start_date)

