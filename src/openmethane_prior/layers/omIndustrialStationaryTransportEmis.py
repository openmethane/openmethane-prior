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

"""Processing industrial stationary transport emissions"""

import numpy as np
import pandas as pd
import rioxarray as rxr
import xarray as xr

from openmethane_prior.config import PriorConfig, load_config_from_env, parse_cli_to_env
from openmethane_prior.grid.regrid import regrid_data
from openmethane_prior.outputs import (
    convert_to_timescale,
    add_ch4_total,
    add_sector,
    create_output_dataset,
    write_output_dataset,
)
from openmethane_prior.raster import remap_raster
import openmethane_prior.logger as logger
from openmethane_prior.sector.sector import SectorMeta

logger = logger.get_logger(__name__)

sector_meta_map = {
    "industrial": SectorMeta(
        name="industrial",
        emission_category="anthropogenic",
        unfccc_categories=["2"], # Industrial Processes
        cf_standard_name="industrial_processes_and_combustion",
    ),
    "stationary": SectorMeta(
        name="stationary",
        emission_category="anthropogenic",
        unfccc_categories=[ # all Energy sectors not in industrial/transport
            "1.A.1.b", # Petroleum refining
            "1.A.1.c", # Manufacture of solid fuels and other energy industries
            "1.A.2", # Manufacturing industries and construction
            "1.A.4", # Other sectors
            "1.A.5", # Other (as specified in table 1.A(a) sheet 4)
            "1.C", # Transport and storage
        ],
        cf_standard_name="industrial_energy_production",
    ),
    "transport": SectorMeta(
        name="transport",
        emission_category="anthropogenic",
        unfccc_categories=["1.A.3"], # Transport
        cf_standard_name="land_transport",
    ),
}


def processEmissions(config: PriorConfig, prior_ds: xr.Dataset):
    """
    Process emissions for Industrial, Stationary and Transport sectors, adding
    them to the prior dataset.
    """
    logger.info("processEmissions for Industrial, Stationary and Transport")

    ntlData = rxr.open_rasterio(
        config.as_input_file(config.layer_inputs.ntl_path), masked=False
    )
    # sum over three bands
    ntlt = ntlData.sum(axis=0)
    np.nan_to_num(ntlt, copy=False)

    om_ntlt = remap_raster(ntlt, config.domain_grid(), AREA_OR_POINT=ntlData.AREA_OR_POINT)

    # limit emissions to land points
    inventory_mask_regridded = regrid_data(config.inventory_dataset()['inventory_mask'], from_grid=config.inventory_grid(), to_grid=config.domain_grid())
    om_ntlt *= inventory_mask_regridded

    # now collect total nightlights across inventory domain
    inventory_ntlt = remap_raster(ntlt, config.inventory_grid(), AREA_OR_POINT=ntlData.AREA_OR_POINT)

    # now mask to region of inventory
    inventory_ntlt *= config.inventory_dataset()['inventory_mask']

    # we want proportions of total for scaling emissions
    om_ntlt_proportion = om_ntlt / inventory_ntlt.sum().item()

    """ note that this is the correct scaling since remap_raster accumulates so
    that quotient is the proportion of total nightlights in that cell """
    sector_totals = pd.read_csv(
        config.as_input_file(config.layer_inputs.sectoral_emissions_path)
    ).to_dict(orient="records")[0]

    for sector, sector_meta in sector_meta_map.items():
        # allocate the proportion of the total to each grid cell
        sector_emissions = om_ntlt_proportion * sector_totals[sector] * 1e9
        add_sector(
            prior_ds=prior_ds,
            sector_data=convert_to_timescale(sector_emissions, config.domain_grid().cell_area),
            sector_meta=sector_meta,
        )


if __name__ == "__main__":
    parse_cli_to_env()
    config = load_config_from_env()

    ds = create_output_dataset(config)
    processEmissions(config, ds)
    add_ch4_total(ds)
    write_output_dataset(config, ds)
