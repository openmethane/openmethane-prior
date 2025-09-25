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
import attrs
import pathlib

from openmethane_prior.data_manager.asset import DataAsset
from openmethane_prior.data_manager.source import DataSource

import openmethane_prior.logger as logger

logger = logger.get_logger(__name__)


@attrs.define()
class DataManager:

    data_path: pathlib.Path
    """Folder on the filesystem where fetched data will be stored"""

    data_sources: dict[str, DataSource] = attrs.Factory(dict)
    """All data sources managed by this data manager, by 'name'"""

    data_assets: dict[str, DataAsset] = attrs.Factory(dict)
    """All data assets that have been fetched and processed"""

    def add_source(self, source: DataSource):
        """Add a data source to this data manager"""
        # a DataSource with the same name was already added
        # this may not be a problem if the DataSource is used by more than
        # one sector / process.
        existing_source = self.data_sources.get(source.name)
        if existing_source is not None:
            if existing_source.url and existing_source.url != source.url:
                logger.warn(f"multiple DataSource instances with name '{source.name}' providing different URLs")

        self.data_sources[source.name] = source

    def prepare_asset(self, source: DataSource) -> DataAsset:
        """Fetch and process data sources, turning them into data assets that
        are ready to be used."""
        expected_save_path = self.data_path / source.file_name

        # if the file is already present on the filesystem, do not attempt to
        # re-fetch it
        if expected_save_path.exists():
            data_asset = DataAsset(
                name=source.name,
                path=expected_save_path,
            )
        else:
            save_path = source.fetch(self.data_path)

            # warn and move on
            if save_path != expected_save_path:
                logger.warn(f"asset '{source.name}' actual save path '{save_path}' does not match expected save path '{expected_save_path}'")

            data_asset = DataAsset(
                name=source.name,
                path=save_path,
            )

        # cache the asset for any subsequent get calls
        self.data_assets[source.name] = data_asset

        return data_asset

    def get_asset(self, source: DataSource) -> DataAsset | None:
        """Get a data asset by fetching and processing a data source."""
        self.add_source(source)

        asset = self.data_assets.get(source.name)
        if asset is None:
            asset = self.prepare_asset(source)

        return asset
