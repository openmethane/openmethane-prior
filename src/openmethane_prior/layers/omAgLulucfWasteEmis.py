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

"""
Process livestock methane emissions
"""

import csv
import warnings

import numpy as np
import pyproj
import rioxarray as rxr
import xarray as xr
from openmethane_prior.omInputs import (
    domainProj,
    livestockDataPath,
    sectoralEmissionsPath,
    sectoralMappingsPath,
)
from openmethane_prior.omInputs import domainXr as ds
from openmethane_prior.omOutputs import (
    convertToTimescale,
    landuseReprojectionPath,
    sumLayers,
    writeLayer,
)
from openmethane_prior.omUtils import area_of_rectangle_m2, secsPerYear
from tqdm import tqdm


def processEmissions():
    # Load raster land-use data
    print("processEmissions for Agriculture, LULUCF and waste")
    print("Loading land use data")
    landUseData = rxr.open_rasterio(landuseReprojectionPath, masked=True)

    ## Calculate livestock CH4
    print("Calculating livestock CH4")
    with xr.open_dataset(livestockDataPath) as lss:
        ls = lss.load()

    # use the landmask layer to establish the shape of the domain grid
    landmask = ds.LANDMASK
    _, lmy, lmx = landmask.shape

    # Re-project into domain coordinates
    # - create meshgrids of the lats and lons
    lonmesh, latmesh = np.meshgrid(ls.lon, ls.lat)

    # create a pyproj transformer
    tx = pyproj.Transformer.from_crs("EPSG:4326", domainProj.crs)

    # Transform/reproject - the output is a 2D array of x distances, and a 2D array of y distances
    print("Reprojecting livestock data")
    x1, y1 = tx.transform(latmesh, lonmesh)

    ww = ds.DX * lmx
    hh = ds.DY * lmy

    xDomain = np.floor((x1 + ww / 2) / ds.DX).astype(int)
    yDomain = np.floor((y1 + hh / 2) / ds.DY).astype(int)

    # calculate areas in m2 of grid cells
    print("Calculate areas in m2 of livestock data")
    latEnteric = ls.lat.values
    lonEnteric = ls.lon.values
    dlatEnteric = latEnteric[1] - latEnteric[0]
    dlonEnteric = lonEnteric[1] - lonEnteric[0]
    lonEnteric_edge = np.zeros(len(lonEnteric) + 1)
    lonEnteric_edge[0:-1] = lonEnteric - dlonEnteric / 2.0
    lonEnteric_edge[-1] = lonEnteric[-1] + dlonEnteric / 2.0
    # lonEnteric_edge = np.around(lonEnteric_edge,2)
    latEnteric_edge = np.zeros(len(latEnteric) + 1)
    latEnteric_edge[0:-1] = latEnteric - dlatEnteric / 2.0
    latEnteric_edge[-1] = latEnteric[-1] + dlatEnteric / 2.0
    # latEnteric_edge = np.around(latEnteric_edge,2)

    nlonEnteric = len(lonEnteric)
    nlatEnteric = len(latEnteric)

    areas = np.zeros((nlatEnteric, nlonEnteric))
    # take advantage of regular grid to compute areas equal for each gridbox at same latitude
    for iy in range(nlatEnteric):
        areas[iy, :] = (
            area_of_rectangle_m2(
                latEnteric_edge[iy],
                latEnteric_edge[iy + 1],
                lonEnteric_edge[0],
                lonEnteric_edge[-1],
            )
            / lonEnteric.size
        )

    livestockCH4 = np.zeros((lmy, lmx))
    # convert unit from kg/year/cell to kg/year/m2
    CH4 = lss.CH4_total.values / areas

    print("Distribute livestock CH4 (long process)")
    # Precalculate masks for each row and column of the target for faster processing
    x_masks = np.asarray([xDomain == i for i in range(lmx)])
    y_masks = [yDomain == i for i in range(lmy)]

    for j in tqdm(range(lmy)):
        if y_masks[j].sum() == 0:
            # Early exit if no livestock data in this row
            continue

        # Get a subset of y_data that is of interest for the rest of the loop
        y_data = CH4[y_masks[j]]

        # Numpy warns about taking means of missing slices
        # This happens for the cases where the xDomain is empty for the given yDomain
        with warnings.catch_warnings():
            warnings.simplefilter(category=RuntimeWarning, action="ignore")
            filtered_x_masks = x_masks[:, y_masks[j]]
            filtered_y_data = [y_data[x_mask_subset].mean() for x_mask_subset in filtered_x_masks]

        assert len(filtered_y_data) == lmx

        livestockCH4[j, :] = np.nan_to_num(filtered_y_data, nan=0)

    modelAreaM2 = ds.DX * ds.DY
    livestockCH4Total = (livestockCH4 * modelAreaM2).sum()  # total emissions in kg

    print("Calculating sectoral emissions")
    # Import a map of land use type numbers to emissions sectors
    landuseSectorMap = {}
    with open(sectoralMappingsPath, newline="") as f:
        reader = csv.reader(f)
        next(reader)  # toss headers

        for value, sector in reader:
            if sector:
                landuseSectorMap[int(value)] = sector

    # Import a map of emissions per sector, store it to hash table
    methaneInventoryBySector = {}
    seenHeaders = False
    headers = []

    with open(sectoralEmissionsPath, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not seenHeaders:
                headers = row.copy()
                seenHeaders = True
            else:
                methaneInventoryBySector = dict.fromkeys(headers, 0)
                for i, v in enumerate(headers):
                    ch4 = float(row[i]) * 1e9  # convert Mt to kgs

                    # subtract the livestock ch4 from agricuture
                    if v == "agriculture":
                        ch4 -= livestockCH4Total

                    methaneInventoryBySector[v] = ch4

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
            sectorEmissionsPerGridSquare[sector] = methaneInventoryBySector[sector] / numGridSquares
            sectorsUsed.append(sector)

    methane = {}
    for sector in sectorsUsed:
        methane[sector] = np.zeros(landmask.shape)

    print("Mapping land use grid to domain grid")
    xDomain = np.floor((landUseData.x + ww / 2) / ds.DX).values.astype(int)
    yDomain = np.floor((landUseData.y + hh / 2) / ds.DY).values.astype(int)

    print("Assigning methane layers to domain grid")
    for landUseType, _ in usageCounts.items():
        sector = landuseSectorMap[landUseType]
        emission = sectorEmissionsPerGridSquare[sector]
        sectorPixels = np.argwhere(dataBand == landUseType)

        if emission > 0:
            for y, x in sectorPixels:
                try:
                    methane[sector][0][yDomain[y]][xDomain[x]] += emission
                except IndexError:
                    # print("ignoring out of range pixel")
                    pass  # it's outside our domain

    print("Writing sectoral methane layers output file")
    for sector in sectorsUsed:
        writeLayer(f"OCH4_{sector.upper()}", convertToTimescale(methane[sector]))

    print("Writing livestock methane layers output file")
    # convert the livestock data from per year to per second and write
    livestockLayer = np.zeros(landmask.shape)
    livestockLayer[0] = livestockCH4 / secsPerYear
    writeLayer("OCH4_LIVESTOCK", livestockLayer)


if __name__ == "__main__":
    processEmissions()
    sumLayers()
