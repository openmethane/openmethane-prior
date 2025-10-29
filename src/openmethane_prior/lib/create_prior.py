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

from .config import PriorConfig
from .data_manager.manager import DataManager
from .inputs import check_input_files
from .outputs import create_output_dataset, add_ch4_total, add_sector
from .sector.config import PriorSectorConfig
from .sector.sector import PriorSector


def create_prior(config: PriorConfig, sectors: list[PriorSector]):
    """
    Calculate the prior methane emissions estimate for Open Methane

    Parameters
    ----------
    config
        Configuration used for the calculation
    sectors
        List of PriorSector objects to process
    """
    if config.start_date is None:
        raise ValueError("Start date must be provided")

    data_manager = DataManager(data_path=config.input_path, prior_config=config)
    check_input_files(config)

    # Initialise the output dataset based on the domain provided in config
    prior_ds = create_output_dataset(config)

    sector_config = PriorSectorConfig(prior_config=config, data_manager=data_manager)

    for sector in sectors:
        # all sector modules must implement a create_estimate method
        if not callable(sector.create_estimate):
            raise ValueError("PriorSector module must include a create_estimate function")

        # calculate the emissions for the sector
        sector_data = sector.create_estimate(sector, sector_config, prior_ds)

        # add the sector emissions to the output
        add_sector(
            prior_ds=prior_ds,
            sector_data=sector_data,
            sector_meta=sector,
        )

    add_ch4_total(prior_ds)

    return prior_ds
