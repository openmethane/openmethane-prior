from omInputs import electricityPath, fugitivesPath, landUsePath, sectoralEmissionsPath, sectoralMappingsPath, ntlPath, auShapefilePath, livestockDataPath, termiteFilePath, wetlandFilePath
import requests
import os
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
termiteFileFile = getenv("TERMITES")
wetlandFileFile = getenv("WETLANDS")

downloads = [
    [electricityFile, electricityPath],
    [fugitivesFile, fugitivesPath],
    [landUseFile, landUsePath],
    [sectoralEmissionsFile, sectoralEmissionsPath],
    [sectoralMappingsFile, sectoralMappingsPath],
    [ntlFile, ntlPath],
    [auShapefileFile, auShapefilePath],
    [livestockDataFile, livestockDataPath],
    [termiteFileFile, termiteFilePath],
    [wetlandFileFile, wetlandFilePath]
]

for filename, filepath in downloads:
    url = f"{remote}{filename}"

    if not os.path.exists(filepath):
        print(f"Downloading {filename} to {filepath} from {url}")

        with requests.get(url, stream=True) as response:
            with open(filepath, mode="wb") as file:
                for chunk in response.iter_content(chunk_size=10 * 1024):
                    file.write(chunk)
    else:
        print(f"Skipping {filename} beacuse it already exists at {filepath}")