import os
from pathlib import Path

import dotenv
import pytest
import xarray as xr


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
def cro_xr(root_dir, env):
    cro_file_path = os.path.join(root_dir, os.environ["CROFILE"])
    return xr.open_dataset(cro_file_path)


@pytest.fixture()
def dot_xr(root_dir, env):
    dot_file_path = os.path.join(root_dir, os.environ["DOTFILE"])
    return xr.open_dataset(dot_file_path)
