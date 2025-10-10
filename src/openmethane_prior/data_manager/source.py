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
from __future__ import annotations
from typing import Callable

import attrs
import os
import pathlib
import urllib.request

from openmethane_prior.config import PriorConfig


def file_name_from_url(_self: DataSource, prior_config: PriorConfig) -> str:
    if _self.url is None:
        raise ValueError("DataSource: if url is not specified, file_name must be provided")
    return os.path.basename(_self.url)


def basic_fetch(data_source: ConfiguredDataSource) -> pathlib.Path:
    """Fetches a DataSource where a url is provided, and saves it in the
    provided data_path."""
    if data_source.url is None:
        raise ValueError("DataSource must have url set to use default fetch")

    full_path = data_source.data_path / data_source.file_name
    full_path.parent.mkdir(parents=True, exist_ok=True)

    save_path, response = urllib.request.urlretrieve(
        url=data_source.url,
        # try to use a predictable save path so we can check if the file
        # already exists
        filename=full_path,
    )
    # urlretrieve will throw on non-successful fetches

    return pathlib.Path(save_path)


@attrs.define()
class DataSource:
    """
    DataSource is a minimal representation of a source of data, usually a
    single file, detailing where or how to fetch it and, if necessary, how it
    should be preprocessed.

    When a DataSource has been fetched and processed, it is represented by
    a DataAsset.
    """

    name: str = attrs.field()
    """Unique, machine-friendly name that can be used to identify this data"""

    url: str = attrs.field(default=None)
    """Publicly accessible URL where this data can be downloaded"""

    file_name: str | Callable[[DataSource, PriorConfig], str] = attrs.field(
        default=file_name_from_url,
    )
    """The name of the file that this data source will be downloaded to.
    Defaults to the filename (part after the last /) of the url, but if the
    downloaded file will have a different name, it should be specified here.

    This is used to determine if the file is already in the data path, so
    fetching can be skipped on subsequent runs.
    
    Can be provided as a string, or a function."""

    fetch: Callable[[ConfiguredDataSource], pathlib.Path] = attrs.field(
        default=basic_fetch,
    )
    """A method which takes the DataSource and PriorConfig and fetches the
    represented data. If the data is available at a static, publicly accessible
    URL, then this method can be omitted and the url attribute can be provided
    instead."""


@attrs.define()
class ConfiguredDataSource:
    """
    ConfiguredDataSource is derived from a DataSource once specific prior
    parameters have been introduced. It has a static file_name, even when the
    DataSource ir originated from has a file_name function, etc.
    """

    name: str
    """Unique, machine-friendly name that can be used to identify this data"""

    url: str
    """Publicly accessible URL where this data can be downloaded"""

    file_name: str
    """The name of the file that this data source will be downloaded to"""

    fetch: Callable[[ConfiguredDataSource], pathlib.Path]
    """Method to fetch the data if it is not already present"""

    data_path: pathlib.Path
    """Path where input data should be saved"""

    prior_config: PriorConfig
    """Configuration for the current run of the prior"""


def configure_data_source(
        data_source: DataSource,
        prior_config: PriorConfig,
        data_path: pathlib.Path,
):
    """Create a ConfiguredDataSource from a DataSource and a PriorConfig"""
    file_name = data_source.file_name
    if callable(file_name):
        file_name = file_name(data_source, prior_config)

    return ConfiguredDataSource(
        name=data_source.name,
        url=data_source.url,
        file_name=file_name,
        fetch=data_source.fetch,
        prior_config=prior_config,
        data_path=data_path,
    )
