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

from openmethane_prior.config import PriorConfig, load_config_from_env, parse_cli_to_env
from openmethane_prior.data_manager.manager import DataManager
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
from openmethane_prior.outputs import add_ch4_total, create_output_dataset, write_output_dataset
from openmethane_prior.sector.config import PriorSectorConfig
from openmethane_prior.verification import verify_emis
import openmethane_prior.logger as logger

logger = logger.get_logger(__name__)

prettyprinter.install_extras(["attrs"])

all_sectors = [
    omAgLulucfWasteEmis,
    omIndustrialStationaryTransportEmis,
    omElectricityEmis,
    omFugitiveEmis,
    omTermiteEmis,
    omWetlandEmis,
    omGFASEmis,
]


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

    data_manager = DataManager(data_path=config.input_path, prior_config=config)
    check_input_files(config)

    # Initialise the output dataset based on the domain provided in config
    prior_ds = create_output_dataset(config)

    sector_config = PriorSectorConfig(prior_config=config, data_manager=data_manager)

    for sector in all_sectors:
        # all sector modules must implement a processEmissions method
        # TODO: implement an abstract class interface
        if not callable(sector.processEmissions):
            raise ValueError("Prior sector module must export a processEmissions function")

        sector.processEmissions(sector_config, prior_ds)

    add_ch4_total(prior_ds)
    verify_emis(config, prior_ds)

    write_output_dataset(config, prior_ds)


if __name__ == "__main__":
    parse_cli_to_env()
    config = load_config_from_env()

    if logger.level <= logging.DEBUG:
        prettyprinter.cpprint(config)

    run_prior(config)
