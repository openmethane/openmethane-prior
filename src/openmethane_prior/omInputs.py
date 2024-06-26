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
"""Input file definitions and checks"""

import os
import sys

import pyproj
import samgeo.common as sam
import xarray as xr

from openmethane_prior import omOutputs
from openmethane_prior.omUtils import getenv

inputsPath = getenv("INPUTS")
climateTracePath = os.path.join(inputsPath, getenv("CLIMATETRACE"))
fossilPath = os.path.join(climateTracePath, getenv("FOSSIL"))

# Input file definitions
domainFilename = getenv("DOMAIN")
domainPath = os.path.join(inputsPath, domainFilename)
electricityPath = os.path.join(inputsPath, getenv("CH4_ELECTRICITY"))
# TODO: Changing this to match with the rest of the download file paths.
# The originally specified directory does not exist and stops the download.
# Maybe needs to be changed back later in the process.
# oilGasPath = os.path.join( fossilPath, getenv("OILGAS"))
oilGasPath = os.path.join(inputsPath, getenv("OILGAS"))
# coalPath = os.path.join( fossilPath, getenv("COAL"))
coalPath = os.path.join(inputsPath, getenv("COAL"))
landUsePath = os.path.join(inputsPath, getenv("LAND_USE"))
sectoralEmissionsPath = os.path.join(inputsPath, getenv("SECTORAL_EMISSIONS"))
sectoralMappingsPath = os.path.join(inputsPath, getenv("SECTORAL_MAPPING"))
ntlPath = os.path.join(inputsPath, getenv("NTL"))
auShapefilePath = os.path.join(inputsPath, getenv("AUSF"))
livestockDataPath = os.path.join(inputsPath, getenv("LIVESTOCK_DATA"))
termitePath = os.path.join(inputsPath, getenv("TERMITES"))
wetlandPath = os.path.join(inputsPath, getenv("WETLANDS"))

croFilePath = getenv("CROFILE")
dotFilePath = getenv("DOTFILE")
geomFilePath = getenv("GEO_EM")


# list of layers that will be in the output file
omLayers = [
    "agriculture",
    "electricity",
    "fugitive",
    "industrial",
    "lulucf",
    "stationary",
    "transport",
    "waste",
    "livestock",
    "fire",
    "wetlands",
    "termite",
]

# load the domain info and define a projection once for use in other scripts
print("Loading domain info")
domainXr = None
domainProj = None

if os.path.exists(domainPath):
    with xr.open_dataset(domainPath) as dss:
        domainXr = dss.load()
        domainProj = pyproj.Proj(
            proj="lcc",
            lat_1=domainXr.TRUELAT1,
            lat_2=domainXr.TRUELAT2,
            lat_0=domainXr.MOAD_CEN_LAT,
            lon_0=domainXr.STAND_LON,
            # https://github.com/openmethane/openmethane-prior/issues/24
            # x_0=domainXr.XORIG,
            # y_0=domainXr.YORIG,
            a=6370000,
            b=6370000,
        )


def check_input_file(filename: str, error_msg: str, errors: list[str]):
    """
    Check that a required input file is present

    Parameters
    ----------
    filename
        Path of the required file
    error_msg
        Message to include if the file is missing
    errors
        List of current errors

        If the required file is missing,
        an extra value of `error_msg` is added to the list
    """
    ##
    if not os.path.exists(filename):
        errors.append(error_msg)


def check_input_files():
    """
    Check that all required input files are present

    Exits with an error code of 1 if all required files are not available
    """
    print("### Checking input files...")

    errors = []

    check_input_file(
        domainPath,
        f"Missing file for domain info at {domainPath}, suggest running omCreateDomainInfo.py",
        errors,
    )
    check_input_file(
        electricityPath, f"Missing file for electricity facilities: {electricityPath}", errors
    )
    check_input_file(coalPath, f"Missing file for Coal facilities: {coalPath}", errors)
    check_input_file(oilGasPath, f"Missing file for Oilgas facilities: {oilGasPath}", errors)
    check_input_file(landUsePath, f"Missing file for land use: {landUsePath}", errors)
    check_input_file(
        sectoralEmissionsPath,
        f"Missing file for sectoral emissions: {sectoralEmissionsPath}",
        errors,
    )
    check_input_file(
        sectoralMappingsPath,
        f"Missing file for sectoral emissions mappings: {sectoralMappingsPath}",
        errors,
    )
    check_input_file(ntlPath, f"Missing file for night time lights: {ntlPath}", errors)
    check_input_file(
        livestockDataPath, f"Missing file for livestock data: {livestockDataPath}", errors
    )
    check_input_file(termitePath, f"Missing file for termite data: {termitePath}", errors)
    check_input_file(wetlandPath, f"Missing file for wetlands data: {wetlandPath}", errors)

    ## Print all errors and exit (if we have any errors)
    if len(errors) > 0:
        print(
            "Some required files are missing. "
            "Suggest running omDownloadInputs.py if you're using the default input file set, "
            "and omCreateDomainInfo.py if you haven't already. See issues below."
        )
        print("\n".join(errors))
        sys.exit(1)


def reprojectRasterInputs():
    """Re-project raster files to match domain"""
    print("### Re-projecting raster inputs...")
    sam.reproject(landUsePath, omOutputs.landuseReprojectionPath, domainProj.crs)
    sam.reproject(ntlPath, omOutputs.ntlReprojectionPath, domainProj.crs)
