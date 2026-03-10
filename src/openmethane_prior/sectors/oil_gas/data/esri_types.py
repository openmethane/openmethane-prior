#
# Copyright 2026 The Superpower Institute Ltd.
#
# This file is part of OpenMethane.
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
import datetime
import numpy as np


def map_esri_date_to_date(esri_date_milliseconds) -> datetime.date | None:
    """Convert an esriFieldTypeDate value to UTC datetime.date."""
    if esri_date_milliseconds is None \
            or np.isnan(esri_date_milliseconds) \
            or esri_date_milliseconds <= 0:
        return None

    date_value = datetime.datetime.fromtimestamp(
        esri_date_milliseconds / 1000,
        tz=datetime.timezone.utc,
    )
    return date_value.date()


def map_esri_date_to_str(esri_date_milliseconds) -> str | None:
    """Convert an esriFieldTypeDate value to RFC3339 date string."""
    date = map_esri_date_to_date(esri_date_milliseconds)
    return date.isoformat() if date is not None else None
