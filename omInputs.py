import os
import dotenv
getenv = os.environ.get
dotenv.load_dotenv()

# Input file definitions
domainFilename = getenv("DOMAIN")
domainPath = os.path.join("inputs", domainFilename)
electricityPath = os.path.join("inputs", getenv("CH4_ELECTRICITY"))
fugitivesPath = os.path.join("inputs", getenv("CH4_FUGITIVES"))
landUsePath = os.path.join("inputs", getenv("LAND_USE"))
sectoralEmissionsPath = os.path.join("inputs", getenv("SECTORAL_EMISSIONS"))
sectoralMappingsPath = os.path.join("inputs", getenv("SECTORAL_MAPPING"))
ntlPath = os.path.join("inputs", getenv("NTL"))
auShapefilePath = os.path.join("inputs", getenv("AUSF"))
livestockDataPath = os.path.join("inputs", getenv("LIVESTOCK_DATA"))
termiteFilePath = os.path.join("inputs", getenv("TERMITES"))
wetlandFilePath = os.path.join("inputs", getenv("WETLANDS"))
croFilePath = os.path.join("cmaq_example", getenv("CROFILE"))
dotFilePath = os.path.join("cmaq_example", getenv("DOTFILE"))
geomFilePath = os.path.join("cmaq_example", getenv("GEO_EM"))

import pyproj
import samgeo.common as sam
import xarray as xr
import omOutputs

# list of layers that will be in the output file
omLayers = ["agriculture","electricity","fugitive","industrial","lulucf","stationary","transport","waste","livestock","gfas","wetland","termite"]

# load the domain info and define a projection once for use in other scripts
print("Loading domain info")
domainXr = None
domainProj = None
if os.path.exists(domainPath):
    with xr.open_dataset(domainPath) as dss:
        domainXr = dss.load()
        domainProj = pyproj.Proj(proj='lcc', lat_1=domainXr.TRUELAT1, lat_2=domainXr.TRUELAT2, lat_0=domainXr.MOAD_CEN_LAT, lon_0=domainXr.STAND_LON, a=6370000, b=6370000)

def checkInputFile(file, errorMsg, errors):
    ## Check that all required input files are present
    if not os.path.exists(file):
        errors.append(errorMsg)

def checkInputFiles():
    ## Check that all required input files are present
    print("### Checking input files...")

    errors = []

    checkInputFile(domainPath, f"Missing file for domain: {domainPath}", errors)
    checkInputFile(electricityPath, f"Missing file for electricity facilities: {electricityPath}", errors)
    checkInputFile(fugitivesPath, f"Missing file for fugitive facilities: {fugitivesPath}", errors)
    checkInputFile(landUsePath, f"Missing file for land use: {landUsePath}", errors)
    checkInputFile(sectoralEmissionsPath, f"Missing file for sectoral emissions: {sectoralEmissionsPath}", errors)
    checkInputFile(sectoralMappingsPath, f"Missing file for sectoral emissions mappings: {sectoralMappingsPath}", errors)
    checkInputFile(ntlPath, f"Missing file for night time lights: {ntlPath}", errors)
    checkInputFile(livestockDataPath, f"Missing file for livestock data: {livestockDataPath}", errors)

    ## Print all errors and exit (if we have any errors)
    if len(errors) > 0:
        print("\n".join(errors))
        exit(1)

def reprojectRasterInputs():
    ## Re-project raster files to match domain
    print("### Re-projecting raster inputs...")
    sam.reproject(landUsePath, omOutputs.landuseReprojectionPath, domainProj.crs)
    sam.reproject(ntlPath, omOutputs.ntlReprojectionPath, domainProj.crs)
