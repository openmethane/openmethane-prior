import os
from pathlib import Path

import dotenv
import pytest


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
