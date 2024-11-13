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

"""Process livestock methane emissions"""

import csv

import numpy as np
import rasterio
import rioxarray as rxr
import xarray as xr
from tqdm import tqdm
import pyproj

from openmethane_prior.config import PriorConfig, load_config_from_env
from openmethane_prior.outputs import (
    convert_to_timescale,
    sum_layers,
    write_layer,
)
from openmethane_prior.utils import (
    SECS_PER_YEAR,
    domain_cell_index,
    mask_array_by_sequence,
    )
from openmethane_prior.raster import remap_raster


def processEmissions(config: PriorConfig):  # noqa: PLR0912, PLR0915
    """Process Agriculture LULUCF and Waste emissions"""
    # Load raster land-use data
    print("processEmissions for Agriculture, LULUCF and waste")

    ## Calculate livestock CH4
    print("Calculating livestock CH4")
    with xr.open_dataset(config.as_input_file(config.layer_inputs.livestock_path)) as lss:
        ls = lss.load()

    domain_ds = config.domain_dataset()

    # use the landmask layer to establish the shape of the domain grid
    landmask = domain_ds.LANDMASK
    _, lmy, lmx = landmask.shape

    # Re-project into domain coordinates
    # - create meshgrids of the lats and lons
    lonmesh, latmesh = np.meshgrid(ls.lon, ls.lat)
    xDomain, yDomain = domain_cell_index(config, lonmesh, latmesh)

    enteric_as_array = lss.CH4_total.to_numpy()
    livestockCH4Total = enteric_as_array.sum() # for later correcting ag sector
    livestockCH4 = np.zeros(landmask.shape[-2:])
    print("Distribute livestock CH4 (long process)")
    # we're accumulating emissions from fine to coarse grid
    # accumulate in mass units and divide by area at end
    for j in tqdm(range(ls.lat.size)):
        ix = xDomain[j, :]
        iy = yDomain[j, :]
        # input domain is bigger so mask indices out of range
        mask = (ix >= 0) & (ix < lmx) & (iy >= 0) & (iy < lmy)
        if mask.any():
            # the following needs to use .at method
            # since iy,ix indices may be repeated and we need to acumulate
            np.add.at(livestockCH4, (iy[mask], ix[mask]), enteric_as_array[j, mask])
    # now convert back to flux not emission units
    livestockCH4 /= config.domain_cell_area
    print("Calculating sectoral emissions")
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
    print("Loading land use data")
    # this seems to need two approaches since rioxarray
    # seems to always convert to float which we don't want but we need it for the other tif attributes
    landUseData = rxr.open_rasterio(
        config.as_input_file(config.layer_inputs.land_use_path), masked=True
    )
    lu_x = landUseData.x
    lu_y = landUseData.y
    lu_crs = landUseData.rio.crs
    landUseData.close
    dataBand = rasterio.open(config.as_input_file(config.layer_inputs.land_use_path),
                             engine='rasterio').read()
    dataBand = dataBand.squeeze().transpose() # fixing order and shape
    transform_lu_to_domain = pyproj.Transformer.from_crs(lu_crs,
                                                config.domain_projection().crs).transform
    for sector in landuseSectorMap.keys():
        sector_pixels = mask_array_by_sequence(dataBand, landuseSectorMap[sector])
        total_pixels = sector_pixels.sum()
        sector_xr = xr.DataArray( sector_pixels, coords={'x':lu_x, 'y':lu_y})
        # now aggregate to coarser resolution
        domain_pixels = remap_raster(sector_xr, config, transform=transform_lu_to_domain)
        domain_pixels /=  total_pixels # proportion of national emission in each grid square
        domain_pixels *= methaneInventoryBySector[sector]  # convert to national emissions in kg/gridcell
        write_layer(
            config.output_domain_file,
            f"OCH4_{sector.upper()}",
            convert_to_timescale(domain_pixels, cell_area=config.domain_cell_area),
            config=config,
        )

    print("Writing livestock methane layers output file")
    # convert the livestock data from per year to per second and write
    livestockLayer = np.zeros(landmask.shape)
    livestockLayer[0] = livestockCH4 / SECS_PER_YEAR
    write_layer(
        config.output_domain_file,
        "OCH4_LIVESTOCK",
        livestockLayer,
        config=config,
    )


if __name__ == "__main__":
    config = load_config_from_env()
    processEmissions(config)
    sum_layers(config.output_domain_file)
