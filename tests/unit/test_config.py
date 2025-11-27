import datetime
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


def test_prior_config_input_cache(tmp_path: pathlib.Path):
    data_path = tmp_path / "data"

    cache_path = tmp_path / "cache-test"
    input_path = data_path / "input-test"

    cache_path.mkdir(parents=True)
    cache_test_contents = f"cache test {datetime.datetime.now()}"
    with open(cache_path / "cache-test.txt", "w") as cache_test_file:
        cache_test_file.write(cache_test_contents)

    # create a config with input_cache
    test_config = PriorConfig(
        input_path=input_path,
        output_path=data_path / "out",
        intermediates_path=data_path / "inter",
        input_cache=cache_path,
        domain_path="domain-input.nc",
        inventory_domain_path="domain-input.nc",
        output_filename="out.nc",
    )

    assert not (test_config.input_path / "cache-test.txt").exists()

    test_config.load_cached_inputs()

    assert (test_config.input_path / "cache-test.txt").exists()

    with open(test_config.input_path / "cache-test.txt") as input_file:
        assert input_file.read() == cache_test_contents

    # create a new input in the prior input folder
    cache_test_updated = f"cache updated {datetime.datetime.now()}"
    with open(test_config.input_path / "cache-update.txt", "w") as cache_test_file:
        cache_test_file.write(cache_test_updated)

    # the new file is not copied to the cache yet
    assert not (cache_path / "cache-update.txt").exists()

    # reassign the variable to trigger the PriorConfig deconstructor
    test_config.cache_inputs()

    # updated inputs are copied back to the cache
    assert (cache_path / "cache-update.txt").exists()
    with open(cache_path / "cache-update.txt") as input_file:
        assert input_file.read() == cache_test_updated

    # create a config with a different input_cache
    test_config = PriorConfig(
        input_path=data_path / "new-input",
        output_path=data_path / "out",
        intermediates_path=data_path / "inter",
        input_cache=data_path / "new-cache",
        domain_path="domain-input.nc",
        inventory_domain_path="domain-input.nc",
        output_filename="out.nc",
    )

    # the file from the cache is NOT copied
    assert not (test_config.input_path / "cache-test.txt").exists()