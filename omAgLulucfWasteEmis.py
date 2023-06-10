import csv
import numpy as np
import netCDF4 as nc
import xarray
import rioxarray as rxr
from omInputs import domainPath, sectoralEmissionsPath, sectoralMappingsPath
from omOutputs import landuseReprojectionPath, writeLayer

def processEmissions():
    # Load raster land-use data
    print("Loading land use data")
    landUseData = rxr.open_rasterio(landuseReprojectionPath, masked=True)

    # Load domain
    print("Loading domain dataset")
    ds = nc.Dataset(domainPath)
    landmask = ds["LANDMASK"][:]

    print("Calculating sectoral emissions")
    # Import a map of land use type numbers to emissions sectors
    landuseSectorMap = {}
    with open(sectoralMappingsPath, "r", newline="") as f:
        reader = csv.reader(f)
        next(reader)  # toss headers

        for value, sector in reader:
            if sector:
                landuseSectorMap[int(value)] = sector

    # Import a map of emissions per sector, store it to hash table
    methaneInventoryBySector = {}
    seenHeaders = False
    headers = []

    with open(sectoralEmissionsPath, "r", newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not seenHeaders:
                headers = row.copy()
                seenHeaders = True
            else:
                methaneInventoryBySector = dict.fromkeys(headers, 0)
                for i, v in enumerate(headers):
                    methaneInventoryBySector[v] = float(row[i]) * 1000000

    # Create a dict to count all of the instances of each sector in the land use data
    sectorCounts = dict.fromkeys(methaneInventoryBySector, 0)

    # Read the land use type data band
    dataBand = landUseData[0].values

    # Count all the unique land-use types
    unique, counts = np.unique(dataBand, return_counts=True)
    usageCounts = dict(zip(unique, counts))

    # Filter usage counts down to the land use types we have mapped
    usageCounts = {key: usageCounts[key] for key in landuseSectorMap.keys()}

    # Sum the land use counts into sector counts
    for usageType, count in usageCounts.items():
        sector = landuseSectorMap.get(int(usageType), False)
        if sector:
            sectorCounts[sector] += count

    # Calculate a per grid-square value for each sector
    sectorEmissionsPerGridSquare = dict.fromkeys(methaneInventoryBySector, 0)
    sectorsUsed = []
    for sector, numGridSquares in sectorCounts.items():
        if numGridSquares != 0:
            sectorEmissionsPerGridSquare[sector] = (
                methaneInventoryBySector[sector] / numGridSquares
            )
            sectorsUsed.append(sector)

    _, lmy, lmx = landmask.shape
    ww = ds.DX * lmx
    hh = ds.DY * lmy
    # methane = np.zeros((lmy, lmx))

    methane = {}
    for sector in sectorsUsed:
        methane[sector] = np.zeros(ds["LANDMASK"].shape)

    print("Mapping land use grid to domain grid")
    findGrid = lambda data, totalSize, gridSize: np.floor((data + totalSize / 2) / gridSize)
    xDomain = xarray.apply_ufunc(findGrid, landUseData.x, ww, ds.DX).values.astype(int)
    yDomain = xarray.apply_ufunc(findGrid, landUseData.y, hh, ds.DY).values.astype(int)

    print("Assigning methane layers to domain grid")
    for landUseType, _ in usageCounts.items():
        sector = landuseSectorMap[landUseType]
        emission = sectorEmissionsPerGridSquare[sector]
        sectorPixels = np.argwhere(dataBand == landUseType)

        if emission > 0:
            yDomain = xarray.apply_ufunc(findGrid, landUseData.y, hh, ds.DY).values.astype(int)

            for y, x in sectorPixels:
                try:
                    methane[sector][0][yDomain[y]][xDomain[x]] += emission
                except:
                    print("ignoring out of range pixel")
    

    print("Writing methane layers domain file")
    for sector in sectorsUsed:
        writeLayer(f"OCH4_{sector.upper()}", methane[sector])