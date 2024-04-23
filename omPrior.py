"""
omPrior.py

Copyright 2023 The Superpower Institute Ltd
Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

import argparse
import datetime

import omAgLulucfWasteEmis
import omElectricityEmis
import omGFASEmis
import omIndustrialStationaryTransportEmis
import omInputs
import omOutputs
import omPriorVerify
import omTermiteEmis
import omWetlandEmis

# Parse args
parser = argparse.ArgumentParser(description="Calculate the prior methane emissions estimate for OpenMethane")
parser.add_argument(
    "startDate",
    type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"),
    help="Start date in YYYY-MM-DD format",
)
parser.add_argument(
    "endDate", type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"), help="end date in YYYY-MM-DD format"
)
parser.add_argument("--skip-reproject", default=False, action="store_true")
args = parser.parse_args()

omInputs.checkInputFiles()

if not args.skip_reproject:
    omInputs.reprojectRasterInputs()

omAgLulucfWasteEmis.processEmissions()
omIndustrialStationaryTransportEmis.processEmissions()
omElectricityEmis.processEmissions()
# omFugitiveEmis.processEmissions(args.startDate, args.endDate)

omTermiteEmis.processEmissions()
omGFASEmis.processEmissions(args.startDate, args.endDate)
omWetlandEmis.processEmissions(args.startDate, args.endDate)

omOutputs.sumLayers()

omPriorVerify.verifyEmis()
