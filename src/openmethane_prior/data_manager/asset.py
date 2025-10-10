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


@attrs.define()
class DataAsset:
    """
    DataAsset is a file which is ready to be used. Usually it would represent a
    DataSource which has been fetched and processed.
    """

    name: str
    """Unique, machine-friendly name that can be used to identify this data"""

    path: pathlib.Path
    """Path on the local file system where the data is stored"""

