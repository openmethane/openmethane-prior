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

"""Main entry point for running the openmethane-prior"""
import logging
import prettyprinter

from openmethane_prior.lib import (
    load_config_from_env,
    logger,
    parse_cli_to_env,
    create_prior,
)
from openmethane_prior.lib.verification import verify_emis
from openmethane_prior.sectors import all_sectors

logger = logger.get_logger(__name__)

prettyprinter.install_extras(["attrs"])


if __name__ == "__main__":
    parse_cli_to_env()
    config = load_config_from_env()

    if logger.level <= logging.DEBUG:
        prettyprinter.cpprint(config)

    # if no sectors were specified, process all sectors
    sectors = list(all_sectors)
    if config.sectors is not None:
        sectors = [s for s in sectors if s.name in config.sectors]

    prior_ds = create_prior(config, sectors)

    # check if estimates are within expected thresholds
    verify_emis(sectors, config, prior_ds)

    # write the output to file
    config.output_file.parent.mkdir(parents=True, exist_ok=True)
    prior_ds.to_netcdf(config.output_file)
