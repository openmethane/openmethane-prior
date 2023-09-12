import argparse
import datetime

import omInputs
import omAgLulucfWasteEmis
import omIndustrialStationaryTransportEmis
import omElectricityEmis
import omFugitiveEmis
import omOutputs
import omPriorVerify

import omGFASEmis
import omTermiteEmis
import omWetlandEmis

# Parse args
parser = argparse.ArgumentParser(description="Calculate the prior methane emissions estimate for OpenMethane")
parser.add_argument('startDate', type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"), help="Start date in YYYY-MM-DD format")
parser.add_argument('endDate', type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"), help="end date in YYYY-MM-DD format")
parser.add_argument("--skip-reproject", default=False, action="store_true")
args = parser.parse_args()

omInputs.checkInputFiles()

if not args.skip_reproject:
    omInputs.reprojectRasterInputs()

omAgLulucfWasteEmis.processEmissions()
omIndustrialStationaryTransportEmis.processEmissions()
omElectricityEmis.processEmissions()
omFugitiveEmis.processEmissions()

omTermiteEmis.processEmissions(ctmDir='.')
omGFASEmis.processEmissions(args.startDate, args.endDate, ctmDir='.')
omWetlandEmis.processEmissions(args.startDate, args.endDate, ctmDir='.')

omOutputs.sumLayers()

omPriorVerify.verifyEmis()