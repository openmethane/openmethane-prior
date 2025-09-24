import os
import pathlib
import pytest

from openmethane_prior.config import PriorConfig, LayerInputs


# This fixture will allow each test to setup the required env variables and
# then reset back to the intial env before the next test
@pytest.fixture(autouse=True)
def env(monkeypatch, root_dir):
    initial_env = dict(os.environ)

    yield

    # Reset environment to initial state
    os.environ.clear()
    os.environ.update(initial_env)

@pytest.fixture
def mock_layer_inputs(tmp_path):
    # mock paths to fake filenames
    return LayerInputs(
        aus_shapefile_path=pathlib.Path("./AUSF.nc"),
    )

def test_prior_config(tmp_path: pathlib.Path, mock_layer_inputs):
    test_config = PriorConfig(
        remote="http://example.com",
        input_path=tmp_path / "in",
        output_path=tmp_path / "out",
        intermediates_path=tmp_path / "inter",
        domain_path="domain-input.nc",
        inventory_domain_path="domain-input.nc",
        output_filename="out.nc",
        layer_inputs=mock_layer_inputs,
    )

    assert test_config.as_input_file("test.nc") == tmp_path / "in" / "test.nc"
    assert test_config.as_output_file("test.nc") == tmp_path / "out" / "test.nc"
    assert test_config.as_intermediate_file("test.nc") == tmp_path / "inter" / "test.nc"

    assert test_config.domain_file == tmp_path / "in" / "domain-input.nc"
    assert test_config.inventory_domain_file == tmp_path / "in" / "domain-input.nc"
    assert test_config.output_file == tmp_path / "out" / "out.nc"
