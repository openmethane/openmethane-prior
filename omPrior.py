import argparse
import omInputs
import omAgLulucfWasteEmis
import omIndustrialStationaryTransportEmis
import omElectricityEmis
import omFugitiveEmis
import omOutputs
import omPriorVerify

# Parse args
parser = argparse.ArgumentParser(description="Calculate the prior methane emissions estimate for OpenMethane")
parser.add_argument("--skip-reproject", default=False, action="store_true")
args = parser.parse_args()

omInputs.checkInputFiles()

if not args.skip_reproject:
    omInputs.reprojectRasterInputs()

omAgLulucfWasteEmis.processEmissions()
omIndustrialStationaryTransportEmis.processEmissions()
omElectricityEmis.processEmissions()
omFugitiveEmis.processEmissions()

omOutputs.sumLayers()

omPriorVerify.verifyEmis()