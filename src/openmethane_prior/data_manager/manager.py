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

    data_assets: dict[str, DataSource] = attrs.Factory(dict)
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

    def ready_assets(self):
        """Fetch and process data sources, turning them into data assets that
        are ready to be used."""
        for source in self.data_sources.values():
            save_path = source.fetch(self.data_path)

            self.data_assets[source.name] = DataAsset(
                name=source.name,
                path=save_path,
            )

    def get_asset(self, name: str) -> DataAsset | None:
        """Get a data asset by its name."""
        asset = self.data_assets.get(name)
        if asset is None:
            if self.data_sources.get(name) is None:
                raise ValueError(f"Asset '{name}' not found")
            raise ValueError(f"Asset '{name}' not ready, call ready_assets() to prepare assets")

        return self.data_assets.get(name)
