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
"""Input file definitions and checks"""

import urllib.request

from openmethane_prior.lib.config import PriorConfig
import openmethane_prior.lib.logger as logger
from openmethane_prior.lib.utils import is_url

logger = logger.get_logger(__name__)


def check_input_files(config: PriorConfig):
    """
    Check that all required input files are present

    Exits with an error code of 1 if all required files are not available
    """
    logger.debug("Checking input files")

    config.input_path.mkdir(parents=True, exist_ok=True)

    errors = []
    if not config.domain_file.exists():
        if is_url(config.domain_path):
            save_path, response = urllib.request.urlretrieve(
                url=config.domain_path,
                filename=config.domain_file,
            )
        else:
            errors.append(f"\n- {config.domain_file} (domain info)")

    if not config.inventory_domain_file.exists():
        if is_url(config.inventory_domain_path):
            save_path, response = urllib.request.urlretrieve(
                url=config.inventory_domain_path,
                filename=config.inventory_domain_file,
            )
        else:
            errors.append(f"\n- {config.inventory_domain_file} (inventory domain)")

    ## Print all errors and exit (if we have any errors)
    if len(errors) > 0:
        logger.warning(
            "Required inputs are missing. "
            f"\nMissing inputs:{''.join(errors)}"
        )
        raise ValueError("Required inputs are missing")
