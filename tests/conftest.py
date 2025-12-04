import os
import pathlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Generator

import dotenv
import pytest
import xarray as xr

from openmethane_prior.lib import create_prior
from openmethane_prior.lib.config import PriorConfig, load_config_from_env, PriorConfigOptions
from openmethane_prior.lib.data_manager.manager import DataManager
from openmethane_prior.lib.grid.create_grid import create_grid_from_mcip
from openmethane_prior.lib.grid.grid import Grid
from openmethane_prior.lib.inputs import check_input_files
from openmethane_prior.lib.sector.config import PriorSectorConfig
from openmethane_prior.sectors import all_sectors


@pytest.fixture(scope="session")
def root_dir() -> pathlib.Path:
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def cache_dir(root_dir) -> pathlib.Path:
    return root_dir / "data/.cache"


# This fixture will be automatically used by all tests to setup the required env variables
@pytest.fixture(autouse=True)
def env(monkeypatch, root_dir):
    initial_env = dict(os.environ)

    # Use the example .env file to drive the tests
    dotenv.load_dotenv(dotenv_path=root_dir / ".env.example", override=True)

    yield

    # Reset environment to initial state
    os.environ.clear()
    os.environ.update(initial_env)


@pytest.fixture(scope="session")
def config_params(start_date, end_date) -> PriorConfigOptions:
    return dict(
        start_date=start_date,
        end_date=end_date,
        domain_path="https://openmethane.s3.amazonaws.com/domains/au-test/v1/domain.au-test.nc",
        inventory_domain_path="https://openmethane.s3.amazonaws.com/domains/aust10km/v1/domain.aust10km.nc",
    )


@pytest.fixture()
def config(tmp_path_factory, config_params, cache_dir) -> PriorConfig:
    """Default configuration

    Uses a new temporary directory for each test, but a shared input_cache to
    prevent refetching input files in each test.
    """
    data_dir = tmp_path_factory.mktemp("data")
    return load_config_from_env(
        **config_params,
        input_path=data_dir / "inputs",
        intermediates_path=data_dir / "intermediates",
        output_path=data_dir / "outputs",
        input_cache=cache_dir,
    )


@pytest.fixture()
def input_files(config):
    """This fixture isn't required for tests that must use input files, but it
    will cause input files to be loaded from a shared cache to prevent
    refetching.

    Tests that don't use this fixture will have a clean input folder for every
    test, and will fetch any remote DataSources requested by the DataManager
    which may be intended, ie for testing input fetching."""
    config.load_cached_inputs()

    # fetch configured domains
    check_input_files(config)

    yield

    config.cache_inputs()

    # remove input files once test completes, as each copy of the input folder
    # is ~1GB, and many copies will be made during a full test suite run.
    shutil.rmtree(config.input_path)


@pytest.fixture()
def data_manager(config) -> DataManager:
    return DataManager(data_path=config.input_path, prior_config=config)


@pytest.fixture()
def sector_config(config) -> PriorSectorConfig:
    data_manager = DataManager(data_path=config.input_path, prior_config=config)
    sector_config = PriorSectorConfig(prior_config=config, data_manager=data_manager)
    return sector_config


@pytest.fixture(scope="session")
def start_date() -> datetime.date:
    """Default configuration

    Uses the same range of dates for each test
    """
    return datetime.strptime("2022-12-07", "%Y-%m-%d")


@pytest.fixture(scope="session")
def end_date() -> datetime.date:
    """Default configuration

    Uses the same range of dates for each test
    """
    return datetime.strptime("2022-12-08", "%Y-%m-%d")


@pytest.fixture()
def input_domain(config, input_files) -> Generator[xr.Dataset, None, None]:
    """
    Get an input domain

    Returns
    -------
        The input domain as an xarray dataset
    """
    assert config.domain_file.exists()

    yield config.domain_dataset()


@pytest.fixture(scope="session")
def prior_emissions_ds(
    cache_dir,
    config_params,
    tmp_path_factory,
) -> Generator[xr.Dataset, None, None]:
    """
    Run the output domain

    Returns
    -------
        The calculated output domain
    """
    data_dir = tmp_path_factory.mktemp("data")
    config = load_config_from_env(
        **config_params,
        input_path=data_dir / "inputs",
        intermediates_path=data_dir / "intermediates",
        output_path=data_dir / "outputs",
        input_cache=cache_dir,
    )

    # run the prior and return the result
    return create_prior(config, all_sectors)


@pytest.fixture()
def aust10km_grid() -> Grid:
    """
    Return a large Grid with a non-standard projection.
    :return: Grid
    """
    # aust10km projection details
    return create_grid_from_mcip(
        TRUELAT1=-15.0,
        TRUELAT2=-40.0,
        MOAD_CEN_LAT=-27.643997,
        STAND_LON=133.302001953125,
        COLS=454,
        ROWS=430,
        XCENT=133.302001953125,
        YCENT=-27.5,
        XORIG=-2270000.0,
        YORIG=-2165629.25,
        XCELL=10000.0,
        YCELL=10000.0,
    )