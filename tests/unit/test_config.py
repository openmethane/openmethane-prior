import datetime
import os
import pathlib
import pytest

from openmethane_prior.lib.config import PriorConfig


# This fixture will allow each test to setup the required env variables and
# then reset back to the initial env before the next test
@pytest.fixture()
def reset_env(monkeypatch):
    initial_env = dict(os.environ)
    os.environ.clear()

    yield

    # Reset environment to initial state
    os.environ.clear()
    os.environ.update(initial_env)


def test_prior_config_defaults(start_date, end_date):
    test_config = PriorConfig(
        domain_path="domain.nc",
        inventory_domain_path="inventory.nc",
        start_date=start_date,
        end_date=end_date,
    )

    assert test_config.domain_path == "domain.nc"
    assert test_config.inventory_domain_path == "inventory.nc"
    assert test_config.start_date == start_date
    assert test_config.end_date == end_date

    # defaults
    assert test_config.sectors is None
    assert test_config.input_path == pathlib.Path("data/inputs")
    assert test_config.output_path == pathlib.Path("data/outputs")
    assert test_config.intermediates_path == pathlib.Path("data/intermediates")
    assert test_config.output_filename == "prior-emissions.nc"
    assert test_config.input_cache is None

    test_config_none = PriorConfig(
        domain_path="domain.nc",
        inventory_domain_path="inventory.nc",
        start_date=start_date,
        end_date=end_date,
        input_path=None,
        output_path=None,
        intermediates_path=None,
        output_filename=None,
    )

    # defaults
    assert test_config_none.input_path == pathlib.Path("data/inputs")
    assert test_config_none.output_path == pathlib.Path("data/outputs")
    assert test_config_none.intermediates_path == pathlib.Path("data/intermediates")
    assert test_config_none.output_filename == "prior-emissions.nc"


def test_prior_config_full(tmp_path: pathlib.Path, start_date, end_date):
    test_config = PriorConfig(
        domain_path="domain.nc",
        inventory_domain_path="inventory.nc",
        start_date=start_date,
        end_date=end_date,
        input_path=tmp_path / "in",
        output_path=tmp_path / "out",
        intermediates_path=tmp_path / "inter",
        output_filename="out.nc",
    )

    assert test_config.as_input_file("test.nc") == tmp_path / "in" / "test.nc"
    assert test_config.as_output_file("test.nc") == tmp_path / "out" / "test.nc"
    assert test_config.as_intermediate_file("test.nc") == tmp_path / "inter" / "test.nc"

    assert test_config.domain_file == tmp_path / "in" / "domain.nc"
    assert test_config.inventory_domain_file == tmp_path / "in" / "inventory.nc"
    assert test_config.output_file == tmp_path / "out" / "out.nc"


def test_prior_config_from_env(reset_env, start_date, end_date):
    os.environ["DOMAIN_FILE"] = "env-domain.nc"
    os.environ["INVENTORY_DOMAIN_FILE"] = "env-inventory.nc"
    os.environ["START_DATE"] = "2023-01-01"
    os.environ["END_DATE"] = "2023-01-31"
    os.environ["SECTORS"] = "agriculture,coal,waste"
    os.environ["INPUTS"] = "env/in"
    os.environ["OUTPUTS"] = "env/out"
    os.environ["INTERMEDIATES"] = "env/inter"
    os.environ["INPUT_CACHE"] = "env/cache"
    os.environ["OUTPUT_FILENAME"] = "env-output.nc"

    test_config = PriorConfig.from_env()

    assert test_config.domain_path == "env-domain.nc"
    assert test_config.inventory_domain_path == "env-inventory.nc"
    assert test_config.start_date == datetime.datetime(2023, 1, 1, 0, 0, 0)
    assert test_config.end_date == datetime.datetime(2023, 1, 31, 0, 0, 0)
    assert test_config.sectors == ("agriculture", "coal", "waste")
    assert test_config.input_path == pathlib.Path("env/in")
    assert test_config.output_path == pathlib.Path("env/out")
    assert test_config.intermediates_path == pathlib.Path("env/inter")
    assert test_config.input_cache == pathlib.Path("env/cache")
    assert test_config.output_filename == "env-output.nc"


def test_prior_config_input_cache(tmp_path: pathlib.Path, start_date, end_date):
    # these settings are required, but unimportant for the test
    generic_params = dict(
        domain_path="domain.nc",
        inventory_domain_path="inventory.nc",
        start_date=start_date,
        end_date=end_date,
    )

    data_path = tmp_path / "data"
    cache_path = tmp_path / "cache-test"

    # created some cached content
    cache_path.mkdir(parents=True)
    cache_test_contents = f"cache test {datetime.datetime.now()}"
    with open(cache_path / "cache-test.txt", "w") as cache_test_file:
        cache_test_file.write(cache_test_contents)

    # create a config with input_cache
    test_config = PriorConfig(
        **generic_params,
        input_path=data_path / "input-test",
        input_cache=cache_path,
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
        **generic_params,
        input_path=data_path / "new-input",
        input_cache=data_path / "new-cache",
    )

    # the file from the cache is NOT copied
    assert not (test_config.input_path / "cache-test.txt").exists()