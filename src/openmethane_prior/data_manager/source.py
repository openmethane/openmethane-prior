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
from typing import Any, Callable

import attrs
import os
import pathlib
import urllib.request

from openmethane_prior.config import PriorConfig
from openmethane_prior.data_manager.asset import DataAsset


def file_path_from_url(_self: DataSource, prior_config: PriorConfig) -> str:
    if _self.url is None:
        raise ValueError("DataSource: if url is not specified, file_path must be provided")
    return os.path.basename(_self.url)


def basic_fetch(data_source: ConfiguredDataSource) -> pathlib.Path:
    """Fetches a DataSource where a url is provided, and saves it in the
    provided data_path."""
    if data_source.url is None:
        raise ValueError("DataSource must have url set to use default fetch")

    save_path, response = urllib.request.urlretrieve(
        url=data_source.url,
        # predictable path so we can check if the file already exists
        filename=data_source.asset_path,
    )
    # urlretrieve will throw on non-successful fetches

    return pathlib.Path(save_path)


@attrs.define()
class DataSource:
    """
    DataSource is a minimal representation of a source of data, usually a
    single file, detailing where or how to fetch it and, if necessary, how it
    should be preprocessed.

    If no url or fetch method is configured and only a file_path is provided,
    it's recommended to include some instructions for users on how to obtain
    the file.

    When a DataSource has been fetched and processed, it is represented by
    a DataAsset.
    """

    name: str = attrs.field()
    """Unique, machine-friendly name that can be used to identify this data"""

    url: str = attrs.field(default=None)
    """Publicly accessible URL where this data can be downloaded"""

    file_path: str | pathlib.Path | Callable[[DataSource, PriorConfig], str] = attrs.field(
        default=file_path_from_url,
    )
    """Optional path to the file on the local filesystem. By default this is
    derived automatically from the url parameter and should not be specified.
    If the downloaded file will have a different file name or a fetch method
    is provided, then file_path should be set to the expected filename.

    If no url or fetch method is provided, this can be set to an absolute path,
    or a path relative to the DataManager data_path. It's recommended to
    provide some guidance to users on how the file can be obtained.
    
    Can be provided as a string, or a function."""

    fetch: Callable[[ConfiguredDataSource], pathlib.Path] = attrs.field(
        default=basic_fetch,
    )
    """A method which takes the DataSource and PriorConfig and fetches the
    represented data. If the data is available at a static, publicly accessible
    URL, then this method can be omitted and the url attribute can be provided
    instead."""

    parse: Callable[[ConfiguredDataSource], Any] | None = attrs.field(
        default=None,
    )
    """An optional method which can read in the fetched data file and parse it
    into a data structure which is usable directly by sector modules.
    The parse method has access to prior configuration so it can use prior
    parameters such as start and end date, or domain grids.
    
    Note: parsed data structures will persist in memory after being read
    until the program exits. If a parsed data structure will result in a large
    memory footprint and will only be used by a single sector, it may be better
    to parse the data in the layer implementation so it can be freed.
    """

    data_sources: list[DataSource] = attrs.field(factory=list)
    """If this data source depends on other data sources, they can be provided
    in data_sources to ensure they will be loaded first."""


@attrs.define()
class ConfiguredDataSource:
    """
    ConfiguredDataSource is derived from a DataSource once specific prior
    parameters have been introduced. It has a static file_path, even when the
    DataSource it originated from has a file_path function, etc.
    """

    name: str
    """Unique, machine-friendly name that can be used to identify this data"""

    url: str
    """Publicly accessible URL where this data can be downloaded"""

    asset_path: pathlib.Path
    """The full path to the fetched file asset"""

    source_fetch: Callable[[ConfiguredDataSource], pathlib.Path]
    """Method to fetch the data if it is not already present.
    Not to be called directly, use .fetch() instead."""

    source_parse: Callable[[ConfiguredDataSource], Any] | None
    """Method to parse fetched data into a usable data structure.
    Not to be called directly, use .parse() instead."""

    data_path: pathlib.Path
    """Path where input data should be saved"""

    prior_config: PriorConfig
    """Configuration for the current run of the prior"""

    data_assets: list[DataAsset]
    """Assets loaded from DataSources defined in DataSource.data_sources"""

    @property
    def parseable(self) -> bool:
        return self.source_parse is not None

    def fetch(self):
        """Fetches the data to the data_path using the provided source_fetch
         method
        """
        self.asset_path.parent.mkdir(parents=True, exist_ok=True)
        return self.source_fetch(self)

    def parse(self):
        """Reads and parses the asset data using the provided source_parse
        method
        """
        return self.source_parse(self)


def configure_data_source(
        data_source: DataSource,
        prior_config: PriorConfig,
        data_path: pathlib.Path,
        data_assets: list[DataAsset] = None,
):
    """Create a ConfiguredDataSource from a DataSource and a PriorConfig"""
    file_path = data_source.file_path
    if callable(file_path):
        file_path = file_path(data_source, prior_config)

    asset_path = file_path if os.path.isabs(file_path) else data_path / file_path

    return ConfiguredDataSource(
        name=data_source.name,
        url=data_source.url,
        asset_path=pathlib.Path(asset_path),
        source_fetch=data_source.fetch,
        source_parse=data_source.parse,
        prior_config=prior_config,
        data_path=data_path,
        data_assets=data_assets if data_assets is not None else [],
    )
