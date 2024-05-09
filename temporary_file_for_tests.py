import os
import dotenv

dotenv.load_dotenv()
getenv = os.environ.get

remote = getenv("PRIOR_REMOTE")

electricityFile = getenv("CH4_ELECTRICITY")
fugitivesFile = getenv("CH4_FUGITIVES")
landUseFile = getenv("LAND_USE")
sectoralEmissionsFile = getenv("SECTORAL_EMISSIONS")
sectoralMappingsFile = getenv("SECTORAL_MAPPING")
ntlFile = getenv("NTL")
auShapefileFile = getenv("AUSF")
livestockDataFile = getenv("LIVESTOCK_DATA")
termiteFile = getenv("TERMITES")
wetlandFile = getenv("WETLANDS")
coalFile = getenv("COAL")
oilGasFile = getenv("OILGAS")

inputsPath = getenv("INPUTS")
cmaqExamplePath = getenv("CMAQ_EXAMPLE")
climateTracePath = os.path.join( inputsPath, getenv("CLIMATETRACE"))
fossilPath = os.path.join( climateTracePath, getenv("FOSSIL"))

electricityPath = os.path.join(inputsPath, getenv("CH4_ELECTRICITY"))
oilGasPath = os.path.join( fossilPath, getenv("OILGAS"))
coalPath = os.path.join( fossilPath, getenv("COAL"))
landUsePath = os.path.join(inputsPath, getenv("LAND_USE"))
sectoralEmissionsPath = os.path.join(inputsPath, getenv("SECTORAL_EMISSIONS"))
sectoralMappingsPath = os.path.join(inputsPath, getenv("SECTORAL_MAPPING"))
ntlPath = os.path.join(inputsPath, getenv("NTL"))
auShapefilePath = os.path.join(inputsPath, getenv("AUSF"))
livestockDataPath = os.path.join(inputsPath, getenv("LIVESTOCK_DATA"))
termitePath = os.path.join(inputsPath, getenv("TERMITES"))
wetlandPath = os.path.join(inputsPath, getenv("WETLANDS"))

downloads = [
    [electricityFile, electricityPath],
    [coalFile, coalPath],
    [oilGasFile, oilGasPath],
    [landUseFile, landUsePath],
    [sectoralEmissionsFile, sectoralEmissionsPath],
    [sectoralMappingsFile, sectoralMappingsPath],
    [ntlFile, ntlPath],
    [auShapefileFile, auShapefilePath],
    [livestockDataFile, livestockDataPath],
    [termiteFile, termitePath],
    [wetlandFile, wetlandPath]
]