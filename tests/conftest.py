# Arrange
import pytest
from pathlib import Path
@pytest.fixture
def root_dir():
    return Path(__file__).parent.parent