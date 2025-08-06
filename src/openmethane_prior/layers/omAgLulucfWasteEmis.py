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

import numpy as np
import rasterio
import rioxarray as rxr
import xarray as xr

from openmethane_prior.config import PriorConfig, load_config_from_env, parse_cli_to_env
from openmethane_prior.outputs import (
    convert_to_timescale,
    add_ch4_total,
    add_sector,
    create_output_dataset, write_output_dataset,
)
from openmethane_prior.utils import SECS_PER_YEAR, mask_array_by_sequence
from openmethane_prior.raster import remap_raster
import openmethane_prior.logger as logger

logger = logger.get_logger(__name__)

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
    logger.info("processEmissions for Agriculture, LULUCF and waste")

    ## Calculate livestock CH4
    logger.info("Calculating livestock CH4")
    with xr.open_dataset(config.as_input_file(config.layer_inputs.livestock_path)) as lss:
        ls = lss.load()

    domain_grid = config.domain_grid()

    # Re-project into domain coordinates
    # - create meshgrids of the lats and lons
    lonmesh, latmesh = np.meshgrid(ls.lon, ls.lat)
    cell_x, cell_y, cell_valid = domain_grid.lonlat_to_cell_index(lonmesh, latmesh)

    enteric_as_array = lss.CH4_total.to_numpy()
    livestockCH4Total = enteric_as_array.sum() # for later correcting ag sector
    livestockCH4 = np.zeros(domain_grid.shape)
    logger.info("Distribute livestock CH4 (long process)")
    # we're accumulating emissions from fine to coarse grid
    # accumulate in mass units and divide by area at end
    for j in range(ls.lat.size):
        ix, iy = cell_x[j,:], cell_y[j,:]
        # input domain is bigger so mask indices out of range
        mask = cell_valid[j, :]
        if mask.any():
            # the following needs to use .at method since iy,ix indices may be repeated and we need to acumulate
            np.add.at(livestockCH4, (iy[mask], ix[mask]), enteric_as_array[j, mask])
    # now convert back to flux not emission units
    livestockCH4 /= domain_grid.cell_area

    # Import a map of land use type numbers to emissions sectors
    # make a dictionary of all landuse types corresponding to sectors in map
    landuseSectorMap = {}
    sectoral_mapping_file = config.as_input_file(config.layer_inputs.sectoral_mapping_path)
    with open(sectoral_mapping_file, newline="") as f:
        reader = csv.reader(f)
        next(reader)  # toss headers

        for value, sector in reader:
            if sector:
                if sector in landuseSectorMap:
                    landuseSectorMap[sector].append(int(value))
                else:
                    landuseSectorMap[sector] = [int(value)]
    # Import a map of emissions per sector, store it to hash table
    methaneInventoryBySector = {}
    with open(config.as_input_file(config.layer_inputs.sectoral_emissions_path), newline="") as f:
        reader = csv.reader(f)
        headers = next(reader                       ) # first line
        row = next(reader)
        methaneInventoryBySector = {h:float(row[i])*1e9 for i,h in enumerate(headers)} # converting from mtCH4 to kgCH4
    # subtract the livestock ch4 from agriculture
    methaneInventoryBySector["agriculture"] -= livestockCH4Total
    # Read the land use type data band
    logger.debug("Loading land use data")
    # this seems to need two approaches since rioxarray
    # seems to always convert to float which we don't want but we need it for the other tif attributes
    landUseData = rxr.open_rasterio(
        config.as_input_file(config.layer_inputs.land_use_path), masked=True
    )
    lu_x = landUseData.x
    lu_y = landUseData.y
    lu_crs = landUseData.rio.crs
    landUseData.close()

    dataBand = rasterio.open(
        config.as_input_file(config.layer_inputs.land_use_path),
        engine='rasterio',
    ).read()
    dataBand = dataBand.squeeze()

    for sector in landuseSectorMap.keys():
        logger.debug(f"Processing land use for sector {sector}")
        # create a mask of pixels which match the sector code
        sector_mask = mask_array_by_sequence(dataBand, landuseSectorMap[sector])
        sector_xr = xr.DataArray(sector_mask, coords={ 'y': lu_y, 'x': lu_x  })

        # now aggregate to coarser resolution of the domain grid
        sector_gridded = remap_raster(sector_xr, config.domain_grid(), input_crs=lu_crs)

        # apply land mask before counting any land use
        sector_gridded *= prior_ds["land_mask"]

        sector_gridded /=  sector_gridded.sum() # proportion of national emission in each grid square
        sector_gridded *= methaneInventoryBySector[sector]  # convert to national emissions in kg/gridcell

        add_sector(
            prior_ds=prior_ds,
            sector_name=sector.lower(),
            sector_data=convert_to_timescale(sector_gridded, cell_area=domain_grid.cell_area),
            sector_standard_name=sectorEmissionStandardNames[sector],
        )

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

