import os
import pathlib
import shutil
from datetime import datetime
from pathlib import Path
import pytest
import xarray as xr

from openmethane_prior.lib import (
    PriorConfig,
    PriorParameters,
    DataManager,
    Domain,
)
from openmethane_prior.lib.config import fetch_domain
from openmethane_prior.lib.grid.create_grid import create_grid_from_mcip
from openmethane_prior.lib.grid.grid import Grid


TEST_DOMAIN_URL="https://openmethane.s3.amazonaws.com/domains/au-test/v1/domain.au-test.nc"

@pytest.fixture(scope="session")
def root_dir() -> pathlib.Path:
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def cache_dir(root_dir) -> pathlib.Path:
    return root_dir / "data/.cache"


@pytest.fixture(scope="session")
def cache_dir(root_dir) -> pathlib.Path:
    return root_dir / "data/.cache"


@pytest.fixture()
def config(tmp_path_factory, cache_dir, start_date, end_date) -> PriorConfig:
    """Default configuration

    Uses a new temporary directory for each test, but a shared input_cache to
    prevent refetching input files in each test.
    """
    data_dir = tmp_path_factory.mktemp("data")
    config = PriorConfig(
        start_date=start_date,
        end_date=end_date,
        domain_path=TEST_DOMAIN_URL,
        input_path=data_dir / "inputs",
        intermediates_path=data_dir / "intermediates",
        output_path=data_dir / "outputs",
        input_cache=cache_dir,
    )
    config.prepare_paths()
    return config


@pytest.fixture()
def input_files(config):
    """Pre-fetch domain inputs from the shared cache.

    Tests that don't use this fixture will have a clean input folder for every
    test, and will fetch any remote DataSources on demand — which may be
    intended when testing input fetching."""
    config.load_cached_inputs()

    yield

    config.cache_inputs()

    # remove input files once test completes, as each copy of the input folder
    # is ~1GB, and many copies will be made during a full test suite run.
    shutil.rmtree(config.input_path)


@pytest.fixture()
def cached_domain_path(tmp_path, cache_dir):
    """Load test domain file from cache to avoid re-fetch on every test. If not
    present, fetch and cached the file for subsequent tests."""
    # if the input_cache already has the domain file in it, copy it across so
    # it doesn't have to be downloaded on every test
    domain_file = os.path.basename(TEST_DOMAIN_URL)
    domain_cache_path = cache_dir / domain_file
    domain_local_path = tmp_path / domain_file
    if domain_cache_path.exists() and not domain_local_path.exists():
        shutil.copy(domain_cache_path, domain_local_path)
    else:
        domain_local_path = fetch_domain(TEST_DOMAIN_URL, tmp_path)
        # store the fetched file back in the cache for the next test
        domain_cache_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(domain_local_path, domain_cache_path)
    return domain_local_path


@pytest.fixture()
def params(cached_domain_path, start_date, end_date):
    """Default per-run parameters, without a full PriorConfig."""
    return PriorParameters(
        domain=Domain.from_file(cached_domain_path),
        start_date=start_date,
        end_date=end_date,
    )


@pytest.fixture()
def config_params(config) -> PriorParameters:
    """Default per-run parameters."""
    return PriorParameters.from_config(config)


@pytest.fixture()
def data_manager(input_files, config, config_params) -> DataManager:
    """DataManager with the domain already resolved (input_files fetches it)."""
    return DataManager(
        data_path=config.input_path,
        intermediates_path=config.intermediates_path,
        prior_params=config_params,
    )


@pytest.fixture()
def data_manager_fetch_only(config, config_params) -> DataManager:
    return DataManager(
        data_path=config.input_path,
        intermediates_path=config.intermediates_path,
        prior_params=config_params,
        fetch_only=True,
    )


@pytest.fixture(scope="session")
def start_date() -> datetime.date:
    """Default start date used across tests."""
    return datetime.strptime("2022-12-07", "%Y-%m-%d")


@pytest.fixture(scope="session")
def end_date() -> datetime.date:
    """Default end date used across tests."""
    return datetime.strptime("2022-12-08", "%Y-%m-%d")


@pytest.fixture()
def input_domain(params) -> xr.Dataset:
    """Test domain as an xarray dataset"""
    return params.domain.dataset


@pytest.fixture()
def aust10km_grid() -> Grid:
    """Return the aust10km Grid."""
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
