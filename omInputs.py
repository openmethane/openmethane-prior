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
croFilePath = os.path.join("inputs", getenv("croFile"))
dotFilePath = os.path.join("inputs", getenv("dotFile"))
termiteFilePath = os.path.join("inputs", getenv("termiteFile"))
wetlandFilePath = os.path.join("inputs", getenv("wetlandFile"))

import pyproj
import samgeo.common as sam
import xarray as xr
import omOutputs

# create structure for target domain, here we do it from input file, see the file domainPath for the structure
with xr.open_dataset( domainPath) as _:
    domainXr = _.load()

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

    ## Print all errors and exit (if we have any errors)
    if len(errors) > 0:
        print("\n".join(errors))
        exit(1)

def reprojectRasterInputs():
    ## Re-project raster files to match domain
    print("### Re-projecting raster inputs...")
    ds = xr.open_dataset(domainPath)
    domainProj = pyproj.Proj(proj='lcc', lat_1=ds.TRUELAT1, lat_2=ds.TRUELAT2, lat_0=ds.MOAD_CEN_LAT, lon_0=ds.STAND_LON, a=6370000, b=6370000)

    sam.reproject(landUsePath, omOutputs.landuseReprojectionPath, domainProj.crs)
    sam.reproject(ntlPath, omOutputs.ntlReprojectionPath, domainProj.crs)
