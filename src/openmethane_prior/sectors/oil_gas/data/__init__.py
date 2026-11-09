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
"""Data sources for oil and gas emission sources."""

import warnings

# bmi-arcgis-restapi warns on import when Esri's proprietary arcpy library is
# not installed. We only use its REST client, which doesn't need arcpy.
# Importing it here first means the modules in this package get the already
# imported module without the warning.
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message="No Arcpy found", category=UserWarning)
    import restapi  # noqa: F401
