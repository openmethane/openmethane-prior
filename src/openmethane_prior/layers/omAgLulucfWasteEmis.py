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

"""Process agriculture, land use and waste methane emissions"""

import csv
import warnings

import numpy as np
import rioxarray as rxr
import xarray as xr
from tqdm import tqdm

from openmethane_prior.config import PriorConfig, load_config_from_env, parse_cli_to_env
from openmethane_prior.outputs import (
    convert_to_timescale,
    add_ch4_total,
    add_sector,
    create_output_dataset, write_output_dataset,
)
from openmethane_prior.utils import SECS_PER_YEAR, area_of_rectangle_m2

sectorEmissionStandardNames = {
    "agriculture": "agricultural_production",
    "lulucf": "anthropogenic_land_use_change",
    "waste": "waste_treatment_and_disposal",
}


def processEmissions(config: PriorConfig, prior_ds: xr.Dataset):  # noqa: PLR0912, PLR0915
    """
    Process Agriculture LULUCF and Waste emissions, adding them to the prior
    dataset.
    """
    # Load raster land-use data
    print("processEmissions for Agriculture, LULUCF and waste")
    print("Loading land use data")
    landUseData = rxr.open_rasterio(
        config.as_intermediate_file(config.layer_inputs.land_use_path), masked=True
    )

    ## Calculate livestock CH4
    print("Calculating livestock CH4")
    with xr.open_dataset(config.as_input_file(config.layer_inputs.livestock_path)) as lss:
        ls = lss.load()

    domain_grid = config.domain_grid()

    # Re-project into domain coordinates
    # - create meshgrids of the lats and lons
    lonmesh, latmesh = np.meshgrid(ls.lon, ls.lat)
    cell_x, cell_y, cell_valid = domain_grid.lonlat_to_cell_index(lonmesh, latmesh)

    enteric_as_array = lss.CH4_total.to_numpy()
    livestockCH4 = np.zeros(domain_grid.shape)
    print("Distribute livestock CH4 (long process)")
    # we're accumulating emissions from fine to coarse grid
    # accumulate in mass units and divide by area at end
    for j in tqdm(range(ls.lat.size)):
        ix, iy = cell_x[j,:], cell_y[j,:]
        # input domain is bigger so mask indices out of range
        mask = cell_valid[j, :]
        if mask.any():
            # the following needs to use .at method since iy,ix indices may be repeated and we need to acumulate
            np.add.at(livestockCH4, (iy[mask], ix[mask]), enteric_as_array[j, mask])

    livestockCH4Total = livestockCH4.sum()
    # now convert back to flux not emission units
    livestockCH4 /= domain_grid.cell_area

    print("Calculating sectoral emissions")
    # Import a map of land use type numbers to emissions sectors
    landuseSectorMap = {}
    sectoral_mapping_file = config.as_input_file(config.layer_inputs.sectoral_mapping_path)
    with open(sectoral_mapping_file, newline="") as f:
        reader = csv.reader(f)
        next(reader)  # toss headers

        for value, sector in reader:
            if sector:
                landuseSectorMap[int(value)] = sector

    # Import a map of emissions per sector, store it to hash table
    methaneInventoryBySector = {}
    seenHeaders = False
    headers = []

    with open(config.as_input_file(config.layer_inputs.sectoral_emissions_path), newline="") as f:
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
        methane[sector] = np.zeros(domain_grid.shape)

    print("Mapping land use grid to domain grid")
    cell_x, cell_y, cell_valid = domain_grid.xy_to_cell_index(landUseData.x, landUseData.y)

    print("Assigning methane layers to domain grid")
    for landUseType, _ in usageCounts.items():
        sector = landuseSectorMap[landUseType]
        emission = sectorEmissionsPerGridSquare[sector]
        sectorPixels = np.argwhere(dataBand == landUseType)

        if emission > 0:
            for y, x in sectorPixels:
                try:
                    ix, iy = cell_x.item(x), cell_y.item(y)
                    methane[sector][iy, ix] += emission
                except IndexError:
                    # print("ignoring out of range pixel")
                    pass  # it's outside our domain

    print("Writing sectoral methane layers output file")
    for sector in sectorsUsed:
        add_sector(
            prior_ds=prior_ds,
            sector_name=sector.lower(),
            sector_data=convert_to_timescale(methane[sector], cell_area=domain_grid.cell_area),
            sector_standard_name=sectorEmissionStandardNames[sector],
        )

    print("Writing livestock methane layers output file")
    # convert the livestock data from per year to per second and write
    livestock_ch4_s = livestockCH4 / SECS_PER_YEAR
    add_sector(
        prior_ds=prior_ds,
        sector_name="livestock",
        sector_data=livestock_ch4_s,
        sector_standard_name="domesticated_livestock",
    )


if __name__ == "__main__":
    parse_cli_to_env()
    config = load_config_from_env()

    ds = create_output_dataset(config)
    processEmissions(config, ds)
    add_ch4_total(ds)
    write_output_dataset(config, ds)

