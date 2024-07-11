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

import argparse
import datetime

from openmethane_prior.config import PriorConfig, load_config_from_env
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
from openmethane_prior.outputs import sum_layers
from openmethane_prior.raster import reproject_raster_inputs
from openmethane_prior.verification import verify_emis


def run_prior(
    config: PriorConfig, start_date: datetime.date, end_date: datetime.date, skip_reproject: bool
):
    """
    Calculate the prior methane emissions estimate for OpenMethane

    Parameters
    ----------
    config
        Configuration used for the calculation
    start_date
        Date to start the prior calculation (UTC timezone)
    end_date
        Date to end the prior calculation (UTC timezone)
    skip_reproject
        If true, don't reproject the raster datasets onto the domain
    """
    check_input_files(config)

    if not skip_reproject:
        reproject_raster_inputs(config)

    omAgLulucfWasteEmis.processEmissions(config)
    omIndustrialStationaryTransportEmis.processEmissions(config)
    omElectricityEmis.processEmissions(config)
    omFugitiveEmis.processEmissions(config, start_date, end_date)

    omTermiteEmis.processEmissions(config)
    omGFASEmis.processEmissions(config, start_date, end_date)
    omWetlandEmis.processEmissions(config, start_date, end_date)

    sum_layers(config.output_domain_file)
    verify_emis(config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate the prior methane emissions estimate for OpenMethane"
    )
    parser.add_argument(
        "startDate",
        type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"),
        help="Start date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "endDate",
        type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"),
        help="end date in YYYY-MM-DD format",
    )
    parser.add_argument("--skip-reproject", default=False, action="store_true")
    args = parser.parse_args()

    config = load_config_from_env()
    run_prior(
        config=config,
        start_date=args.startDate,
        end_date=args.endDate,
        skip_reproject=args.skip_reproject,
    )
