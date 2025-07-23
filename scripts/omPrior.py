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

import prettyprinter

from openmethane_prior.config import PriorConfig, load_config_from_env, parse_cli_to_env
from openmethane_prior.inputs import check_input_files
from openmethane_prior.layers import (
    omAgLulucfWasteEmis,
    omElectricityEmis,
    omFugitiveEmis,
    omGFASEmis,
    omIndustrialStationaryTransportEmis,
    omTermiteEmis,
    omWetlandEmis,
)
from openmethane_prior.outputs import sum_sectors, initialise_output
from openmethane_prior.raster import reproject_raster_inputs
from openmethane_prior.verification import verify_emis

prettyprinter.install_extras(["attrs"])


def run_prior(config: PriorConfig):
    """
    Calculate the prior methane emissions estimate for Open Methane

    Parameters
    ----------
    config
        Configuration used for the calculation
    """
    if (config.start_date is None):
        raise ValueError("Start date must be provided")

    check_input_files(config)

    # Initialise the output dataset based on the domain provided in config
    initialise_output(config)

    if not config.skip_reproject:
        reproject_raster_inputs(config)

    omAgLulucfWasteEmis.processEmissions(config)
    omIndustrialStationaryTransportEmis.processEmissions(config)
    omElectricityEmis.processEmissions(config)
    omFugitiveEmis.processEmissions(config)

    omTermiteEmis.processEmissions(config)
    omGFASEmis.processEmissions(config)
    omWetlandEmis.processEmissions(config)

    sum_sectors(config.output_file)
    verify_emis(config)


if __name__ == "__main__":
    parse_cli_to_env()
    config = load_config_from_env()

    print("Configuration:")
    prettyprinter.cpprint(config)

    run_prior(config)
