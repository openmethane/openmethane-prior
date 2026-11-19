import errno
import urllib.error

import pandas as pd
import pytest

from openmethane_prior.lib.data_manager.fetchers import (
    check_required_columns,
    download_resumable,
    google_sheet_csv_url,
)


def test_google_sheet_csv_url_from_url():
    result = google_sheet_csv_url(
        "https://docs.google.com/spreadsheets/d/EXAMPLE_SHEET_ID",
        "External facility locations",
    )

    assert result == (
        "https://docs.google.com/spreadsheets/d/EXAMPLE_SHEET_ID/gviz/tq"
        "?tqx=out:csv&headers=1&sheet=External%20facility%20locations"
    )


def test_google_sheet_csv_url_from_id():
    result = google_sheet_csv_url("EXAMPLE_SHEET_ID", "Oil and gas sites")

    assert result == (
        "https://docs.google.com/spreadsheets/d/EXAMPLE_SHEET_ID/gviz/tq"
        "?tqx=out:csv&headers=1&sheet=Oil%20and%20gas%20sites"
    )


def test_check_required_columns():
    df = pd.DataFrame(columns=["Facility name", "Notes", "Site"])

    # no exception: extra columns and order don't matter
    check_required_columns(df, ["Site", "Facility name"], "Test sheet")
    check_required_columns(df, [], "Test sheet")


def test_check_required_columns_missing():
    # a header row joined with the rows below it, as Google produces when it
    # guesses the header spans more than one row
    df = pd.DataFrame(columns=["Facility name Mine A Mine B", "Notes"])

    with pytest.raises(ValueError, match=r"'Test sheet' is missing columns \['Facility name'\]"):
        check_required_columns(df, ["Facility name"], "Test sheet")


class FakeResponse:
    """Serves `body`, raising `error` once `fail_after` bytes have been read."""

    def __init__(self, body: bytes, status: int, headers: dict, fail_after=None, error=None):
        self.body, self.status, self.headers = body, status, headers
        self.fail_after, self.error, self.position = fail_after, error, 0

    def read(self, size):
        if self.fail_after is not None and self.position >= self.fail_after:
            raise self.error
        end = self.position + size
        if self.fail_after is not None:
            end = min(end, self.fail_after)
        block = self.body[self.position : end]
        self.position += len(block)
        return block

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeServer:
    """Stands in for urlopen, serving `data` with Range support. Each entry in
    `behaviours` configures one request; requests beyond them succeed."""

    def __init__(self, data: bytes, behaviours=(), supports_range=True):
        self.data, self.behaviours = data, list(behaviours)
        self.supports_range, self.requests = supports_range, []

    def __call__(self, request, timeout):
        self.requests.append(request)
        behaviour = self.behaviours.pop(0) if self.behaviours else {}
        if "raise" in behaviour:
            raise behaviour["raise"]

        range_header = request.get_header("Range")
        if range_header and self.supports_range:
            start = int(range_header.removeprefix("bytes=").removesuffix("-"))
            body = self.data[start:]
            headers = {
                "Content-Range": f"bytes {start}-{len(self.data) - 1}/{len(self.data)}",
                "Content-Length": str(len(body)),
            }
            status = 206
        else:
            body, status = self.data, 200
            headers = {"Content-Length": str(len(self.data))}
        if behaviour.get("truncate") is not None:
            body = body[: behaviour["truncate"]]
        return FakeResponse(
            body, status, headers, behaviour.get("fail_after"), behaviour.get("error")
        )


DOWNLOAD_DATA = bytes(range(256)) * 4


def test_download_resumable(tmp_path):
    server = FakeServer(DOWNLOAD_DATA)

    path = download_resumable(
        "https://example.com/file.nc", tmp_path / "file.nc", block_size=100, urlopen=server
    )

    assert path.read_bytes() == DOWNLOAD_DATA
    assert len(server.requests) == 1
    assert server.requests[0].get_header("Range") is None


def test_download_resumable_resumes_after_stall(tmp_path):
    # the first response stalls after 300 bytes, the second after 700
    server = FakeServer(
        DOWNLOAD_DATA,
        behaviours=[
            {"fail_after": 300, "error": TimeoutError("read timed out")},
            {"fail_after": 400, "error": ConnectionResetError()},
        ],
    )

    path = download_resumable(
        "https://example.com/file.nc",
        tmp_path / "file.nc",
        retry_delay=0,
        block_size=100,
        urlopen=server,
    )

    assert path.read_bytes() == DOWNLOAD_DATA
    assert [r.get_header("Range") for r in server.requests] == [
        None,
        "bytes=300-",
        "bytes=700-",
    ]



def test_download_resumable_retries_closed_connection(tmp_path):
    # the connection closes cleanly before the full Content-Length is sent
    server = FakeServer(DOWNLOAD_DATA, behaviours=[{"truncate": 600}])

    path = download_resumable(
        "https://example.com/file.nc", tmp_path / "file.nc", retry_delay=0, urlopen=server
    )

    assert path.read_bytes() == DOWNLOAD_DATA
    assert [r.get_header("Range") for r in server.requests] == [None, "bytes=600-"]


def test_download_resumable_without_range_support(tmp_path):
    server = FakeServer(
        DOWNLOAD_DATA,
        behaviours=[{"fail_after": 300, "error": TimeoutError("read timed out")}],
        supports_range=False,
    )

    path = download_resumable(
        "https://example.com/file.nc",
        tmp_path / "file.nc",
        retry_delay=0,
        block_size=100,
        urlopen=server,
    )

    # the server sent the whole file again, which replaced the partial file
    assert path.read_bytes() == DOWNLOAD_DATA
    assert len(server.requests) == 2


def test_download_resumable_client_error(tmp_path):
    not_found = urllib.error.HTTPError("https://example.com/file.nc", 404, "Not Found", {}, None)
    server = FakeServer(DOWNLOAD_DATA, behaviours=[{"raise": not_found}])

    with pytest.raises(urllib.error.HTTPError):
        download_resumable(
            "https://example.com/file.nc", tmp_path / "file.nc", retry_delay=0, urlopen=server
        )

    assert len(server.requests) == 1


def test_download_resumable_gives_up(tmp_path):
    server = FakeServer(DOWNLOAD_DATA, behaviours=[{"raise": TimeoutError("timed out")}] * 3)

    with pytest.raises(TimeoutError):
        download_resumable(
            "https://example.com/file.nc",
            tmp_path / "file.nc",
            max_attempts=3,
            retry_delay=0,
            urlopen=server,
        )

    assert len(server.requests) == 3




@pytest.mark.parametrize("code", [429, 503])
def test_download_resumable_retries_server_errors(tmp_path, code):
    server_error = urllib.error.HTTPError("https://example.com/file.nc", code, "Error", {}, None)
    server = FakeServer(DOWNLOAD_DATA, behaviours=[{"raise": server_error}])

    path = download_resumable(
        "https://example.com/file.nc", tmp_path / "file.nc", retry_delay=0, urlopen=server
    )

    assert path.read_bytes() == DOWNLOAD_DATA
    assert len(server.requests) == 2



def test_download_resumable_without_range_support_gives_up(tmp_path):
    # every response stalls at the same point and can't be resumed, so
    # restarting never gets any further
    server = FakeServer(
        DOWNLOAD_DATA,
        behaviours=[{"fail_after": 300, "error": TimeoutError("read timed out")}] * 4,
        supports_range=False,
    )

    with pytest.raises(TimeoutError):
        download_resumable(
            "https://example.com/file.nc",
            tmp_path / "file.nc",
            max_attempts=3,
            retry_delay=0,
            block_size=100,
            urlopen=server,
        )

    # the first attempt made progress, then 3 attempts restarted without any
    assert len(server.requests) == 4


def test_download_resumable_local_error(tmp_path):
    # local errors, like a full disk, aren't retried
    disk_full = OSError(errno.ENOSPC, "No space left on device")
    server = FakeServer(DOWNLOAD_DATA, behaviours=[{"fail_after": 300, "error": disk_full}])

    with pytest.raises(OSError, match="No space left"):
        download_resumable(
            "https://example.com/file.nc",
            tmp_path / "file.nc",
            retry_delay=0,
            block_size=100,
            urlopen=server,
        )

    assert len(server.requests) == 1
