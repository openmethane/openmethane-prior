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
import pandas as pd
import pathlib
import urllib.parse

from .source import ConfiguredDataSource


def fetch_google_sheet_by_name_csv(
    sheet_id_or_url: str,
    sheet_name: str,
) -> pd.DataFrame:
    """Fetch a single sheet from a publicly viewable Google Sheet and return
    the contents as a pandas DataFrame."""
    if "://docs.google.com" in sheet_id_or_url:
        # if a url is provided, extract the sheet_id
        sheet_url = urllib.parse.urlparse(sheet_id_or_url)
        sheet_id = sheet_url.path.rpartition('/')[-1]
    else:
        sheet_id = sheet_id_or_url

    # make the sheet name url-safe
    sheet_name_param = urllib.parse.quote(sheet_name)

    # Google Sheets provides a CSV endpoint for downloading
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name_param}"
    df = pd.read_csv(url)

    # remove empty columns with no name or data
    for column_name in df.columns:
        if "Unnamed: " in column_name and df[column_name].isnull().all():
            del df[column_name]

    return df


def fetch_google_sheet_csv(sheet_name: str):
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
        df = fetch_google_sheet_by_name_csv(data_source.url, sheet_name)
        df.to_csv(data_source.asset_path, index=False)
        return data_source.asset_path

    return _data_source_fetch