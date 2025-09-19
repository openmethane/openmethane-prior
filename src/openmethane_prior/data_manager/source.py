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

    url: str = None
    """Publically accessible URL where this data can be downloaded"""

    file_name: str = None
    """The name of the file that this data source will be downloaded to.
    Defaults to the filename (part after the last /) of the url, but if the
    downloaded file will have a different name, it should be specified here.
    
    This is used to determine if the file is already in the data path, so
    fetching can be skipped on subsequent runs."""

    def __attrs_post_init__(self):
        if self.file_name is None:
            self.file_name = os.path.basename(self.url)


    def fetch(self, data_path: pathlib.Path) -> pathlib.Path:
        """Download the data from this data source. This can be overridden by
        sub-classing for data sources with more complex fetching logic."""
        if self.url is None:
            raise ValueError("DataSource must have url set to use default fetch")

        data_path.mkdir(parents=True, exist_ok=True)

        save_path, response = urllib.request.urlretrieve(
            url=self.url,
            # try to use a predictable save path so we can check if the file
            # already exists
            filename=data_path / self.file_name,
        )
        # urlretrieve will throw on non-successful fetches

        return pathlib.Path(save_path)