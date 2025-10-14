import os
import pathlib
import pytest

from openmethane_prior.lib.config import PriorConfig


# This fixture will allow each test to setup the required env variables and
# then reset back to the initial env before the next test
@pytest.fixture(autouse=True)
def env(monkeypatch, root_dir):
    initial_env = dict(os.environ)

    yield

    # Reset environment to initial state
    os.environ.clear()
    os.environ.update(initial_env)


def test_prior_config(tmp_path: pathlib.Path):
    test_config = PriorConfig(
        input_path=tmp_path / "in",
        output_path=tmp_path / "out",
        intermediates_path=tmp_path / "inter",
        domain_path="domain-input.nc",
        inventory_domain_path="domain-input.nc",
        output_filename="out.nc",
    )

    assert test_config.as_input_file("test.nc") == tmp_path / "in" / "test.nc"
    assert test_config.as_output_file("test.nc") == tmp_path / "out" / "test.nc"
    assert test_config.as_intermediate_file("test.nc") == tmp_path / "inter" / "test.nc"

    assert test_config.domain_file == tmp_path / "in" / "domain-input.nc"
    assert test_config.inventory_domain_file == tmp_path / "in" / "domain-input.nc"
    assert test_config.output_file == tmp_path / "out" / "out.nc"
