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
def config(tmp_path_factory, config_params) -> PriorConfig:
    """Default configuration

    Uses a new temporary directory for each test
    """
    data_dir = tmp_path_factory.mktemp("data")
    return load_config_from_env(
        **config_params,
        input_path=data_dir / "inputs",
        intermediates_path=data_dir / "intermediates",
        output_path=data_dir / "outputs",
    )


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


@pytest.fixture(scope="session")
def cache_dir(root_dir) -> pathlib.Path:
    return root_dir / ".cache"


@pytest.fixture(scope="session")
def fetch_published_domain(cache_dir) -> list[pathlib.Path]:
    """
    Fetch and cache the domain files.

    Don't use this fixture directly,
    instead use `input_domain` to copy the files to the input directory.

    Returns
    -------
        List of cached input files
    """
    config = load_config_from_env(
        input_path=cache_dir,
        domain_path="https://openmethane.s3.amazonaws.com/domains/au-test/v1/domain.au-test.nc",
        inventory_domain_path="https://openmethane.s3.amazonaws.com/domains/aust10km/v1/domain.aust10km.nc",
    )

    check_input_files(config)

    return list({ # use a set to remove duplicates
        config.domain_file,
        config.inventory_domain_file,
    })


def copy_input_files(
    cache_path: pathlib.Path,
    input_path: pathlib.Path,
    cached_fragments: list[pathlib.Path],
) -> Generator[list[pathlib.Path], None, None]:
    """
    Copy input files from the cache into the input directory

    Parameters
    ----------
    cache_path
        Path to the cache directory
    input_path
        Path to the input directory
    cached_fragments
        List of files that have been cached and should be copied into the input_path.

        Paths should be relative to the cache directory
    """
    files = []
    for fragment in cached_fragments:
        input_file = pathlib.Path(input_path) / fragment
        cached_file = cache_path / fragment
        assert not input_file.exists()

        input_file.parent.mkdir(exist_ok=True, parents=True)

        shutil.copyfile(cached_file, input_file)

        files.append(input_file)

    yield files

    for filepath in files:
        os.remove(filepath)


@pytest.fixture()
def input_files(cache_dir, fetch_published_domain, config) -> Generator[list[pathlib.Path], None, None]:
    """
    Ensure that the required input files are in the input directory.

    The input files are copied from a local cache `.cache`
    """

    files_to_copy = fetch_published_domain

    fragments = [file.relative_to(cache_dir) for file in files_to_copy]
    yield from copy_input_files(cache_dir, config.input_path, fragments)


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
    fetch_published_domain,
    config_params,
    tmp_path_factory,
) -> Generator[xr.Dataset, None, None]:
    """
    Run the output domain

    Returns
    -------
        The calculated output domain
    """
    # Manually copy the input files to the input directory
    # Can't use the config/input_files fixtures because we want to only run this step once
    input_dir = tmp_path_factory.mktemp("inputs")
    intermediate_dir = tmp_path_factory.mktemp("intermediates")
    output_dir = tmp_path_factory.mktemp("outputs")

    config = load_config_from_env(
        **config_params,
        input_path=input_dir,
        intermediates_path=intermediate_dir,
        output_path=output_dir,
    )

    # Use the factory method as input_files has "function" scope
    input_fragments = [
        file.relative_to(cache_dir) for file in fetch_published_domain
    ]
    input_files = next(copy_input_files(cache_dir, config.input_path, input_fragments))

    prior_ds = create_prior(config, all_sectors)

    yield prior_ds

    # Manually clean up any leftover files
    for filepath in input_files:
        os.remove(filepath)


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