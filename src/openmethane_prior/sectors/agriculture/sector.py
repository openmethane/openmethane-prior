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

import numpy as np
import rasterio
import rioxarray as rxr
import xarray as xr

from openmethane_prior.data_sources.inventory import (
    get_sector_emissions_by_code,
    inventory_data_source,
    inventory_domain_data_source,
)
from openmethane_prior.data_sources.landuse import landuse_map_data_source
from openmethane_prior.lib import (
    kg_to_period_cell_flux,
    logger,
    regrid_data,
    remap_raster,
    PriorSectorConfig,
    PriorSector,
)

logger = logger.get_logger(__name__)

# ALUM Classification Version 8
# Source: https://www.agriculture.gov.au/abares/aclump/land-use/alum-classification
alum_codes_agriculture = [
    210, # Grazing native vegetation
    320, # Grazing modified pastures
    420, # Grazing irrigated modified pastures
    520, # Intensive animal production
    521, # Dairy sheds and yards
    522, # Feedlots
    523, # Poultry farms
    524, # Piggeries
    525, # Aquaculture
    526, # Horse studs
    527, # Saleyards/stockyards
    542, # Rural residential with agriculture
]

def process_emissions(
        sector: PriorSector,
        sector_config: PriorSectorConfig,
        prior_ds: xr.Dataset,
):
    config = sector_config.prior_config

    # load the national inventory data, ready to calculate sectoral totals
    emissions_inventory = sector_config.data_manager.get_asset(inventory_data_source).data

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

    inventory_domain = sector_config.data_manager.get_asset(inventory_domain_data_source).data
    inventory_mask_regridded = regrid_data(
        inventory_domain.dataset['inventory_mask'],
        from_grid=inventory_domain.grid,
        to_grid=config.domain().grid,
    )

    # create a mask of pixels which match the sector code
    sector_mask = np.isin(dataBand, alum_codes_agriculture)
    sector_xr = xr.DataArray(sector_mask, coords={ 'y': lu_y, 'x': lu_x  })

    # now aggregate to coarser resolution of the domain grid
    sector_gridded = remap_raster(sector_xr, config.domain().grid, input_crs=lu_crs)

    # apply inventory mask before counting any land use
    sector_gridded *= inventory_mask_regridded

    inventory_gridded = remap_raster(sector_xr, inventory_domain.grid, input_crs=lu_crs)
    # now mask to region of inventory
    inventory_gridded *= inventory_domain.dataset['inventory_mask']

    # calculate the proportion of inventory emissions in each grid cell
    sector_gridded /=  inventory_gridded.sum().item()

    sector_total_emissions = get_sector_emissions_by_code(
        emissions_inventory=emissions_inventory,
        start_date=config.start_date,
        end_date=config.end_date,
        category_codes=sector.unfccc_categories,
    )
    # distribute the emissions reported for the entire sector
    sector_gridded *= sector_total_emissions

    return kg_to_period_cell_flux(sector_gridded, config)


sector = PriorSector(
    name="agriculture",
    emission_category="anthropogenic",
    unfccc_categories=[ # All Agriculture, except cattle and sheep
        "3.A.3", # Enteric Fermentation - Swine
        "3.A.4", # Enteric Fermentation - Other Livestock
        "3.B.3", # Manure Management - Swine
        "3.B.4", # Manure Management - Other Livestock
        "3.C", # Rice Cultivation
        "3.D", # Agricultural Soils
        "3.E", # Prescribed Burning of Savannas
        "3.F", # Field Burning of Agricultural Residues
        "3.G", # Liming
        "3.H", # Urea Application
        "3.I", # Other Carbon-containing Fertilisers
    ],
    cf_standard_name="agricultural_production",
    create_estimate=process_emissions,
)
