#
# Copyright 2025 The Superpower Institute Ltd.
#
# This file is part of Open Methane.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import geopandas as gpd
import http.client
from http import HTTPStatus
import os
import pandas as pd
import pathlib
import ssl
import tempfile
import time
import urllib.error
import urllib.request
import urllib.parse
import zipfile

from .source import ConfiguredDataSource
from openmethane_prior.lib import logger

logger = logger.get_logger(__name__)


def google_sheet_csv_url(sheet_id_or_url: str, sheet_name: str) -> str:
    """Return the URL of the CSV export of a single sheet in a publicly
    viewable Google Sheet."""
    if "://docs.google.com" in sheet_id_or_url:
        # if a url is provided, extract the sheet_id
        sheet_url = urllib.parse.urlparse(sheet_id_or_url)
        sheet_id = sheet_url.path.rpartition('/')[-1]
    else:
        sheet_id = sheet_id_or_url

    # make the sheet name url-safe
    sheet_name_param = urllib.parse.quote(sheet_name)

    # Without headers=1, Google guesses how many rows make up the header. A
    # column that is mostly blank can make it treat most of the sheet as the
    # header, joining every value into one column name.
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq"
        f"?tqx=out:csv&headers=1&sheet={sheet_name_param}"
    )


def check_required_columns(df: pd.DataFrame, required_columns: list[str], sheet_name: str):
    """Raise a ValueError if any of required_columns are missing from df."""
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(
            f"Google Sheet '{sheet_name}' is missing columns {missing_columns}, "
            f"found {list(df.columns)}"
        )


def fetch_google_sheet_by_name_csv(
    sheet_id_or_url: str,
    sheet_name: str,
    required_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Fetch a single sheet from a publicly viewable Google Sheet and return
    the contents as a pandas DataFrame.

    :param required_columns: Column names the sheet must have. A ValueError is
      raised if any are missing. This also catches a renamed sheet, since
      Google returns the first sheet when the named sheet doesn't exist.
    """
    df = pd.read_csv(google_sheet_csv_url(sheet_id_or_url, sheet_name))

    # remove empty columns with no name or data
    for column_name in df.columns:
        if "Unnamed: " in column_name and df[column_name].isnull().all():
            del df[column_name]

    check_required_columns(df, required_columns or [], sheet_name)

    return df


def fetch_google_sheet_csv(sheet_name: str, required_columns: list[str] | None = None):
    """Return a DataSource fetch-compatible method for a DataSource where a
    Google Sheet is specified by the url parameter and only a single sheet
    should be fetched.

    Usage:
        DataSource(
            url="https://docs.google.com/spreadsheets/d/EXAMPLE_SHEET_ID",
            fetch=fetch_google_sheet_csv("Sheet name"),
            ...
        )
    """

    def _data_source_fetch(data_source: ConfiguredDataSource) -> pathlib.Path:
        df = fetch_google_sheet_by_name_csv(data_source.url, sheet_name, required_columns)
        df.to_csv(data_source.asset_path, index=False)
        return data_source.asset_path

    return _data_source_fetch


def fetch_zipped_shp_to_gdf(
    url: str,
    shp_file: str,
) -> gpd.GeoDataFrame:
    """Fetch a zip file specified by DataSource.url, extract the contents and
    read in a Shapefile (.shp) from the archive as a GeoDataFrame."""

    # use a temporary path to store and extract the zip contents, which will
    # be cleaned up automatically afterwards
    with tempfile.TemporaryDirectory(prefix="openmethane-prior") as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir)

        # download and extract the zip file to a known location
        zip_path, response = urllib.request.urlretrieve(
            url=url,
            filename=tmp_path / os.path.basename(url),
        )
        # entire zip must be extracted, as the .shp file depends on sibling files
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmp_path)

        # read the extracted Shapefile with geopandas
        return gpd.read_file(tmp_path / shp_file)


def download_resumable(
    url: str,
    path: pathlib.Path,
    timeout: float = 60,
    max_attempts: int = 10,
    retry_delay: float = 5,
    block_size: int = 1024 * 1024,
    urlopen=urllib.request.urlopen,
) -> pathlib.Path:
    """Download a large file, resuming after stalls and dropped connections.

    urllib.request.urlretrieve has no read timeout, so a connection that
    stops sending data hangs forever, and a failure restarts from zero. Here a
    stalled read raises after `timeout` seconds, and each retry requests only
    the bytes not yet downloaded using an HTTP Range header.

    Parameters
    ----------
    url
        URL of the file to download
    path
        Where to save the file. Any existing file is replaced.
    timeout
        Seconds to wait for the connection or for each read before retrying
    max_attempts
        Consecutive failed attempts allowed. Attempts that extend the
        download further than before reset the count, so a long download can
        survive many stalls.
    retry_delay
        Seconds to wait before the first retry, doubling for each
        consecutive failure up to 5 minutes
    block_size
        Bytes to read and write at a time
    urlopen
        Replaceable for tests

    Returns
    -------
    pathlib.Path
        The path the file was saved to
    """
    offset = 0
    furthest = 0
    failures = 0
    total = None
    with open(path, "wb") as f:
        while True:
            headers = {"Range": f"bytes={offset}-"} if offset else {}
            try:
                request = urllib.request.Request(url, headers=headers)
                with urlopen(request, timeout=timeout) as response:
                    # a server which ignores Range sends the whole file again
                    if offset and response.status != HTTPStatus.PARTIAL_CONTENT:
                        logger.warning(f"{url} doesn't support resuming, restarting download")
                        offset = 0
                        f.seek(0)
                        f.truncate()
                    content_length = response.headers.get("Content-Length")
                    if content_length is not None:
                        total = offset + int(content_length)
                    while block := response.read(block_size):
                        f.write(block)
                        offset += len(block)

                if total is None or offset >= total:
                    return path
                raise http.client.IncompleteRead(b"", total - offset)

            except urllib.error.HTTPError as e:
                # client errors won't be fixed by retrying, except rate limiting
                if (
                    e.code < HTTPStatus.INTERNAL_SERVER_ERROR
                    and e.code != HTTPStatus.TOO_MANY_REQUESTS
                ):
                    raise
                error = e
            # network failures only: local errors such as a full disk are raised
            except (
                urllib.error.URLError,
                ConnectionError,
                TimeoutError,
                ssl.SSLError,
                http.client.HTTPException,
            ) as e:
                error = e

            failures = 0 if offset > furthest else failures + 1
            furthest = max(furthest, offset)
            if failures >= max_attempts:
                raise error
            delay = min(retry_delay * 2 ** max(failures - 1, 0), 300)
            logger.warning(
                f"Download of {url} interrupted at {offset} bytes ({error!r}), "
                f"retrying in {delay:.0f}s"
            )
            time.sleep(delay)
