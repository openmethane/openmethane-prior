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

from openmethane_prior.config import PriorConfig
from openmethane_prior.data_manager.asset import DataAsset
from openmethane_prior.data_manager.source import configure_data_source, ConfiguredDataSource, DataSource

import openmethane_prior.logger as logger

logger = logger.get_logger(__name__)


@attrs.define()
class DataManager:

    data_path: pathlib.Path
    """Folder on the filesystem where fetched data will be stored"""

    prior_config: PriorConfig
    """Configuration for the current run of the prior"""

    data_sources: dict[str, ConfiguredDataSource] = attrs.Factory(dict)
    """All data sources managed by this data manager, by 'name'"""

    data_assets: dict[str, DataAsset] = attrs.Factory(dict)
    """All data assets that have been fetched and processed"""

    def add_source(self, source: DataSource) -> ConfiguredDataSource:
        """Add a data source to this data manager"""
        # a DataSource with the same name was already added
        # this may not be a problem if the DataSource is used by more than
        # one sector / process.
        existing_source = self.data_sources.get(source.name)
        if existing_source is not None:
            if existing_source.url and existing_source.url != source.url:
                logger.warn(f"multiple DataSource instances with name '{source.name}' providing different URLs")

        self.data_sources[source.name] = configure_data_source(
            data_source=source,
            prior_config=self.prior_config,
            data_path=self.data_path,
        )
        return self.data_sources[source.name]

    def prepare_asset(self, source: ConfiguredDataSource) -> DataAsset:
        """Fetch and process data sources, turning them into data assets that
        are ready to be used."""
        # if the file is already present on the filesystem, do not attempt to
        # re-fetch it
        if source.asset_path.exists():
            data_asset = DataAsset(
                name=source.name,
                path=source.asset_path,
            )
        else:
            logger.info(f"Fetching '{source.name}' data source")
            save_path = source.fetch()

            # warn and move on
            if save_path != source.asset_path:
                logger.warn(f"asset '{source.name}' actual path '{save_path}' does not match asset_path '{source.asset_path}'")

            data_asset = DataAsset(
                name=source.name,
                path=save_path,
            )

        # if the DataSource has a "prepare" method to parse or process the
        # data, call it and add the result to the asset
        if source.parseable:
            logger.debug(f"Parsing '{source.name}' data source")
            data_asset.data = source.parse()

        return data_asset

    def get_asset(self, source: DataSource) -> DataAsset:
        """Get a data asset by fetching and processing a data source."""
        configured_source = self.add_source(source)

        asset = self.data_assets.get(source.name)
        if asset is None:
            asset = self.prepare_asset(configured_source)

            # cache the asset for any subsequent get calls
            self.data_assets[source.name] = asset

        return asset
