import os
import pathlib
import shutil
from datetime import datetime
from pathlib import Path

import attrs
import dotenv
import pytest
import xarray as xr
from openmethane_prior.config import PriorConfig, load_config_from_env
from scripts.omCreateDomainInfo import create_domain_info, write_domain_info
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


@pytest.fixture()
def cro_xr(config) -> xr.Dataset:
    return xr.open_dataset(config.cro_file)


@pytest.fixture()
def dot_xr(config) -> xr.Dataset:
    return xr.open_dataset(config.dot_file)


@pytest.fixture()
def config() -> PriorConfig:
    """Default configuration"""
    return load_config_from_env()


# Fixture to download and later remove all input files
@pytest.fixture(scope="session")
def fetch_input_files(root_dir) -> list[pathlib.Path]:
    """
    Fetch and cache the input files.

    Don't use this fixture directly,
    instead use `input_files` to copy the files to the input directory.

    Returns
    -------
        List of cached input files
    """
    config = load_config_from_env()

    fragments = [str(f) for f in attrs.asdict(config.layer_inputs).values()]

    downloaded_files = download_input_files(
        download_path=root_dir / ".cache", fragments=fragments, remote=config.remote
    )

    return downloaded_files


def copy_input_files(input_path: str | pathlib.Path, cached_files: list[pathlib.Path]):
    """
    Copy input files from the cache into the input directory

    Parameters
    ----------
    input_path
        Path to the input directory
    cached_files
        List of files that have been cached and should be copied into the input_path
    """
    files = [input_path / cached_file.name for cached_file in cached_files]

    input_path.mkdir(parents=True, exist_ok=True)

    for cached_file, input_file in zip(cached_files, files):
        try:
            os.remove(input_file)
        except FileNotFoundError:
            pass

        shutil.copyfile(cached_file, input_file)

    yield files

    for filepath in files:
        os.remove(filepath)


@pytest.fixture()
def input_files(root_dir, fetch_input_files, config) -> list[pathlib.Path]:
    """
    Ensure that the required input files are in the input directory.

    The input files are copied from a local cache `.cache`
    """
    yield from copy_input_files(config.input_path, fetch_input_files)


@pytest.fixture(scope="session")
def input_domain(root_dir) -> xr.Dataset:
    """
    Generate the input domain

    Returns
    -------
        The input domain as an xarray dataset
    """
    config = load_config_from_env()

    domain = create_domain_info(
        geometry_file=config.geometry_file,
        cross_file=config.cro_file,
        dot_file=config.dot_file,
    )
    write_domain_info(domain, config.input_domain_file)

    assert config.input_domain_file.exists()

    yield domain

    if config.input_domain_file.exists():
        os.remove(config.input_domain_file)


@pytest.fixture(scope="session")
def output_domain(root_dir, input_domain, fetch_input_files, tmp_path_factory) -> xr.Dataset:
    """
    Run the output domain

    Returns
    -------
        The calculated output domain
    """
    # Manually copy the input files to the input directory
    # Can't use the config/input_files fixtures because we want to only run this step once
    output_dir = tmp_path_factory.mktemp("data")
    config = load_config_from_env(output_path=output_dir)

    # Use the factory method as
    input_files = copy_input_files(config.input_path, fetch_input_files)
    next(input_files)

    run_prior(
        config,
        datetime.strptime("2022-07-01", "%Y-%m-%d"),
        datetime.strptime("2022-07-02", "%Y-%m-%d"),
        False,
    )

    yield xr.load_dataset(config.output_domain_file)

    os.remove(config.output_domain_file)
    next(input_files)  # Cleanup
