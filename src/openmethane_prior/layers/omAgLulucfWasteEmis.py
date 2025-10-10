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
from openmethane_prior.data_manager.manager import DataManager
from openmethane_prior.data_manager.source import DataSource
from openmethane_prior.grid.regrid import regrid_data
from openmethane_prior.inventory.data import create_inventory
from openmethane_prior.outputs import (
    convert_to_timescale,
    add_ch4_total,
    add_sector,
    create_output_dataset, write_output_dataset,
)
from openmethane_prior.inventory.inventory import get_sector_emissions_by_code
from openmethane_prior.sector.config import PriorSectorConfig
from openmethane_prior.sector.sector import SectorMeta
from openmethane_prior.units import kg_to_period_cell_flux
from openmethane_prior.raster import remap_raster
import openmethane_prior.logger as logger

logger = logger.get_logger(__name__)

sector_meta_map = {
    "agriculture": SectorMeta(
        name="agriculture",
        emission_category="anthropogenic",
        unfccc_categories=[ # All Agriculture, except Enteric Fermentation
            "3.B", # Manure Management
            "3.C", # Rice Cultivation
            "3.D", # Agricultural Soils
            "3.E", # Prescribed Burning of Savannas
            "3.F", # Field Burning of Agricultural Residues
            "3.G", # Liming
            "3.H", # Urea Application
            "3.I", # Other Carbon-containing Fertilisers
        ],
        cf_standard_name="agricultural_production",
    ),
    "lulucf": SectorMeta(
        name="lulucf",
        emission_category="anthropogenic",
        unfccc_categories=["4"], # Land Use, Land-Use Change and Forestry
        cf_standard_name="anthropogenic_land_use_change",
    ),
    "waste": SectorMeta(
        name="waste",
        emission_category="anthropogenic",
        unfccc_categories=["5"], # Waste
        cf_standard_name="waste_treatment_and_disposal",
    ),
}

livestock_sector_meta = SectorMeta(
    name="livestock",
    emission_category="anthropogenic",
    unfccc_categories=["3.A"], # Enteric Fermentation
    cf_standard_name="domesticated_livestock",
)

livestock_data_source = DataSource(
    name="enteric-fermentation",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/EntericFermentation.nc",
)
alum_sector_mapping_data_source = DataSource(
    name="alum-sector-mapping",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/landuse-sector-map.csv",
)
# source: https://www.agriculture.gov.au/abares/aclump/land-use/land-use-of-australia-2010-11_2015-16
landuse_map_data_source = DataSource(
    name="landuse-map",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/NLUM_ALUMV8_250m_2015_16_alb.tif",
)

def processEmissions(sector_config: PriorSectorConfig, prior_ds: xr.Dataset):
    """
    Process Agriculture LULUCF and Waste emissions, adding them to the prior
    dataset.
    """
    # Load raster land-use data
    logger.info("processEmissions for Agriculture, LULUCF and waste")
    config = sector_config.prior_config

    ## Calculate livestock CH4
    logger.info("Calculating livestock CH4")
    livestock_asset = sector_config.data_manager.get_asset(livestock_data_source)
    with xr.open_dataset(livestock_asset.path) as lss:
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

    add_sector(
        prior_ds=prior_ds,
        sector_data=convert_to_timescale(livestockCH4, domain_grid.cell_area),
        sector_meta=livestock_sector_meta,
    )

    # Import a map of land use type numbers to emissions sectors
    # make a dictionary of all landuse types corresponding to sectors in map
    landuseSectorMap = {}
    sector_mapping_asset = sector_config.data_manager.get_asset(alum_sector_mapping_data_source)
    with open(sector_mapping_asset.path, newline="") as f:
        reader = csv.reader(f)
        next(reader)  # toss headers

        for value, sector in reader:
            if sector:
                if sector in landuseSectorMap:
                    landuseSectorMap[sector].append(int(value))
                else:
                    landuseSectorMap[sector] = [int(value)]

    # load the national inventory data, ready to calculate sectoral totals
    emissions_inventory = create_inventory(data_manager=sector_config.data_manager)

    # Read the land use type data band
    logger.debug("Loading land use data")
    # this seems to need two approaches since rioxarray
    # seems to always convert to float which we don't want but we need it for the other tif attributes
    landuse_asset = sector_config.data_manager.get_asset(landuse_map_data_source)
    landUseData = rxr.open_rasterio(landuse_asset.path, masked=True)
    lu_x = landUseData.x
    lu_y = landUseData.y
    lu_crs = landUseData.rio.crs
    landUseData.close()

    dataBand = rasterio.open(landuse_asset.path, engine='rasterio').read()
    dataBand = dataBand.squeeze()

    inventory_mask_regridded = regrid_data(config.inventory_dataset()['inventory_mask'], from_grid=config.inventory_grid(), to_grid=config.domain_grid())

    for sector in landuseSectorMap.keys():
        logger.debug(f"Processing land use for sector {sector}")
        # create a mask of pixels which match the sector code
        sector_mask = np.isin(dataBand, landuseSectorMap[sector])
        sector_xr = xr.DataArray(sector_mask, coords={ 'y': lu_y, 'x': lu_x  })

        # now aggregate to coarser resolution of the domain grid
        sector_gridded = remap_raster(sector_xr, config.domain_grid(), input_crs=lu_crs)

        # apply inventory mask before counting any land use
        sector_gridded *= inventory_mask_regridded
        
        inventory_gridded = remap_raster(sector_xr, config.inventory_grid(), input_crs=lu_crs)
        # now mask to region of inventory
        inventory_gridded *= config.inventory_dataset()['inventory_mask']

        # calculate the proportion of inventory emissions in each grid cell
        sector_gridded /=  inventory_gridded.sum().item()

        sector_total_emissions = get_sector_emissions_by_code(
            emissions_inventory=emissions_inventory,
            start_date=config.start_date,
            end_date=config.end_date,
            category_codes=sector_meta_map[sector].unfccc_categories,
        )
        # distribute the emissions reported for the entire sector
        sector_gridded *= sector_total_emissions

        add_sector(
            prior_ds=prior_ds,
            sector_data=kg_to_period_cell_flux(sector_gridded, config),
            sector_meta=sector_meta_map[sector],
        )


if __name__ == "__main__":
    parse_cli_to_env()
    config = load_config_from_env()
    data_manager = DataManager(data_path=config.input_path, prior_config=config)
    sector_config = PriorSectorConfig(prior_config=config, data_manager=data_manager)

    ds = create_output_dataset(config)
    processEmissions(sector_config, ds)
    add_ch4_total(ds)
    write_output_dataset(config, ds)

