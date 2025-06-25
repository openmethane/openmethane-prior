import datetime
import pytest
import sys
import xarray as xr

from openmethane_prior.utils import get_command, get_timestamped_command, time_bounds


def test_get_command():
    command = get_command()

    for arg in sys.argv:
        assert arg in command


def test_get_timestamped_command():
    timestamped_command = get_timestamped_command()

    timestamp = timestamped_command.replace(f": {get_command()}", '')
    parsed = datetime.datetime.fromisoformat(timestamp)

    assert timestamp == parsed.strftime('%Y-%m-%d %H:%M:%S+00:00')


def test_time_bounds():
    start_date = datetime.datetime.fromisoformat('2023-02-01')
    end_date = datetime.datetime.fromisoformat('2023-03-03')

    single_date_range = xr.date_range(start=start_date, end=start_date, use_cftime=True)
    bounds = time_bounds(single_date_range)

    assert len(bounds) == 1
    assert bounds[0] == [single_date_range[0], single_date_range[0] + datetime.timedelta(days=1)]

    multi_date_range = xr.date_range(start=start_date, end=end_date, use_cftime=True)
    bounds = time_bounds(multi_date_range)

    assert len(bounds) == 31
    assert bounds[0] == [multi_date_range[0], multi_date_range[0] + datetime.timedelta(days=1)]
    assert bounds[1] == [multi_date_range[0] + datetime.timedelta(days=1), multi_date_range[0] + datetime.timedelta(days=2)]
    assert bounds[29] == [multi_date_range[-1] - datetime.timedelta(days=1), multi_date_range[-1]]
    assert bounds[30] == [multi_date_range[-1], multi_date_range[-1] + datetime.timedelta(days=1)]
