import pytest
from pathlib import Path


@pytest.fixture(scope="session")
def root_dir():
    return Path(__file__).parent.parent