import os
import pathlib
import shutil
from datetime import datetime
from pathlib import Path
from typing import Generator

import attrs
import dotenv
import pytest
import xarray as xr

from openmethane_prior.config import PriorConfig, PublishedInputDomain, load_config_from_env, PriorConfigOptions
from openmethane_prior.grid.create_grid import create_grid_from_mcip
from openmethane_prior.grid.grid import Grid
from scripts.omDownloadInputs import download_input_files
from scripts.omPrior import run_prior


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
        input_domain=PublishedInputDomain(name="au-test", version="v1"),
        inventory_domain=PublishedInputDomain(name="aust10km", version="v1"),
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
def fetch_published_domain(root_dir) -> list[pathlib.Path]:
    """
    Fetch and cache the domain files.

    Don't use this fixture directly,
    instead use `input_domain` to copy the files to the input directory.

    Returns
    -------
        List of cached input files
    """
    config = load_config_from_env()
    published_domains = [
        PublishedInputDomain(name="au-test", version="v1"), # domain
        PublishedInputDomain(name="aust10km", version="v1"), # inventory
    ]

    fragments = [str(domain.path) for domain in published_domains]

    downloaded_files = download_input_files(
        remote=config.remote,
        download_path=root_dir / ".cache",
        fragments=fragments,
    )

    return downloaded_files


# Fixture to download and later remove all input files
@pytest.fixture(scope="session")
def fetch_input_files(root_dir, config_params) -> list[pathlib.Path]:
    """
    Fetch and cache the input files.

    Don't use this fixture directly,
    instead use `input_files` to copy the files to the input directory.

    Returns
    -------
        List of cached input files
    """
    config = load_config_from_env(**config_params)

    fragments = [str(f) for f in attrs.asdict(config.layer_inputs).values()]

    downloaded_files = download_input_files(
        remote=config.remote,
        download_path=root_dir / ".cache",
        fragments=fragments,
    )

    return downloaded_files


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
def input_files(
    root_dir, fetch_input_files, fetch_published_domain, config,
) -> Generator[list[pathlib.Path], None, None]:
    """
    Ensure that the required input files are in the input directory.

    The input files are copied from a local cache `.cache`
    """
    cache_dir = root_dir / ".cache"
    files_to_copy = fetch_input_files + fetch_published_domain

    fragments = [file.relative_to(cache_dir) for file in files_to_copy]
    yield from copy_input_files(cache_dir, config.input_path, fragments)


@pytest.fixture()
def input_domain(config, root_dir, input_files) -> Generator[xr.Dataset, None, None]:
    """
    Get an input domain

    Returns
    -------
        The input domain as an xarray dataset
    """
    assert config.input_domain_file.exists()

    yield config.domain_dataset()


@pytest.fixture(scope="session")
def prior_emissions_ds(
    root_dir,
    fetch_input_files,
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
    cache_dir = root_dir / ".cache"
    input_fragments = [
        file.relative_to(cache_dir) for file in fetch_input_files + fetch_published_domain
    ]
    input_files = next(copy_input_files(root_dir / ".cache", config.input_path, input_fragments))

    run_prior(config)

    yield xr.load_dataset(config.output_file)

    os.remove(config.output_file)

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