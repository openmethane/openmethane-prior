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
import os
import pathlib
import urllib.request


@attrs.define()
class DataSource:
    """
    DataSource is a minimal representation of a source of data, usually a
    single file, detailing where or how to fetch it and, if necessary, how it
    should be preprocessed.

    When a DataSource has been fetched and processed, it is represented by
    a DataAsset.
    """

    name: str
    """Unique, machine-friendly name that can be used to identify this data"""

    url: str
    """Publically accessible URL where this data can be downloaded"""

    def fetch(self, data_path: pathlib.Path) -> pathlib.Path:
        """Download the data from this data source"""
        file_fragment = os.path.basename(self.url)
        data_path.mkdir(parents=True, exist_ok=True)

        save_path, response = urllib.request.urlretrieve(
            url=self.url,
            filename=data_path / file_fragment,
        )

        # urlretrieve will throw on non-successful fetches

        return pathlib.Path(save_path)
