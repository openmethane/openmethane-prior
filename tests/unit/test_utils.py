import datetime
import numpy as np
import pandas as pd
import sys
import xarray as xr

from openmethane_prior.lib.utils import (
    get_command,
    get_timestamped_command,
    time_bounds,
    bounds_from_cell_edges,
    is_url,
    rows_in_period,
)

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


def test_bounds_from_cell_edges():
    edges = np.arange(11)
    bounds = bounds_from_cell_edges(edges)

    assert len(bounds) == len(edges) - 1
    assert list(bounds[0]) == [edges[0], edges[1]]
    assert list(bounds[-1]) == [edges[-2], edges[-1]]


def test_is_url():
    cases = [
        ("http://example.com", True),
        ("https://example.com", True),
        ("//example.com", False), # "//" scheme not supported
        ("http", False),
        ("http://", False),
        ("https", False),
        ("https://", False),
        ("example.com", False),
        ("", False),
        ("http://example.com/path/to/file.txt", True),
        ("https://example.com/path/to/file.txt", True),
    ]

    for test_url, expected in cases:
        assert is_url(test_url) == expected


def test_rows_in_period():
    dt = lambda st: np.datetime64(datetime.datetime.fromisoformat(st))

    test_df = pd.DataFrame.from_records([
        (dt("2022-12-31T00:00:00Z"), dt("2022-12-31T23:59:59Z"), "a"),
        (dt("2022-12-31T00:00:00Z"), dt("2023-01-01T00:00:00Z"), "b"),
        (dt("2023-01-01T00:00:01Z"), dt("2023-01-01T23:59:59Z"), "c"),
        (dt("2023-01-02T00:00:00Z"), dt("2023-02-02T23:59:59Z"), "d"),
        (dt("2023-01-02T00:00:01Z"), dt("2023-02-02T23:59:59Z"), "e"),
    ], columns=["start_date", "end_date", "test"])

    result_df = rows_in_period(
        test_df,
        start_date=datetime.date(2023, 1, 1),
        end_date=datetime.date(2023, 1, 1),
    )

    assert list(result_df["test"]) == ["b", "c", "d"]

    # works with arbitrary start/end field names "start_test" and "end_test"
    test_df = pd.DataFrame.from_records([
        (dt("2022-12-31T00:00:00Z"), dt("2022-12-31T23:59:59Z"), "f"),
        (dt("2022-12-31T00:00:00Z"), dt("2023-01-01T00:00:00Z"), "g"),
        (dt("2023-01-02T00:00:01Z"), dt("2023-02-02T23:59:59Z"), "h"),
    ], columns=["start_test", "end_test", "test"])

    result_df = rows_in_period(
        test_df,
        start_date=datetime.date(2023, 1, 1),
        end_date=datetime.date(2023, 1, 1),
        start_field="start_test",
        end_field="end_test"
    )

    assert list(result_df["test"]) == ["g"]
