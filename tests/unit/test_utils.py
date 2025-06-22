from datetime import datetime

import pytest
import sys

from openmethane_prior.utils import get_command, get_timestamped_command

def test_get_command():
    command = get_command()

    for arg in sys.argv:
        assert arg in command


def test_get_timestamped_command():
    timestamped_command = get_timestamped_command()

    timestamp = timestamped_command.replace(f": {get_command()}", '')
    parsed = datetime.fromisoformat(timestamp)

    assert timestamp == parsed.strftime('%Y-%m-%d %H:%M:%S+00:00')



