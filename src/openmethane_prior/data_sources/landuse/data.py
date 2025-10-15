#
# Copyright 2023 The Superpower Institute Ltd.
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

from openmethane_prior.lib import DataSource
from openmethane_prior.lib.data_manager.parsers import parse_csv

alum_sector_mapping_data_source = DataSource(
    name="alum-sector-mapping",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/landuse-sector-map.csv",
    parse=parse_csv,
)
# source: https://www.agriculture.gov.au/abares/aclump/land-use/land-use-of-australia-2010-11_2015-16
landuse_map_data_source = DataSource(
    name="landuse-map",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/NLUM_ALUMV8_250m_2015_16_alb.tif",
)
