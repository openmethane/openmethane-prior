import os
import shutil
from pathlib import Path

import attrs
import dotenv
import pytest
import xarray as xr
from openmethane_prior.config import PriorConfig, load_config_from_env
from scripts.omCreateDomainInfo import create_domain_info, write_domain_info
from scripts.omDownloadInputs import download_input_files


@pytest.fixture(scope="session")
def root_dir():
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
def cro_xr(config):
    return xr.open_dataset(config.cro_file)


@pytest.fixture()
def dot_xr(config):
    return xr.open_dataset(config.dot_file)


@pytest.fixture()
def config() -> PriorConfig:
    return load_config_from_env()


# Fixture to download and later remove all input files
@pytest.fixture(scope="session")
def fetch_input_files(root_dir):
    config = load_config_from_env()

    fragments = [str(f) for f in attrs.asdict(config.layer_inputs).values()]

    downloaded_files = download_input_files(
        download_path=root_dir / ".cache", fragments=fragments, remote=config.remote
    )

    return downloaded_files


@pytest.fixture()
def input_files(root_dir, fetch_input_files, config):
    """
    Ensure that the required input files are in the input directory.

    The input files are copied from a local cache `.cache`
    """
    # TODO: check if this is needed
    shutil.rmtree(config.input_path, ignore_errors=True)
    config.input_path.mkdir(parents=True, exist_ok=True)

    files = []
    for cached_file in fetch_input_files:
        copied_file = config.input_path / cached_file.name
        shutil.copyfile(cached_file, copied_file)
        files.append(copied_file)

    yield files

    for filepath in files:
        os.remove(filepath)


@pytest.fixture(scope="session")
def input_domain(root_dir):
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
