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
import xarray as xr

from openmethane_prior.lib import (
    logger,
    PriorSectorConfig,
    kg_to_period_cell_flux,
)
from openmethane_prior.data_sources.inventory import get_sector_emissions_by_code, inventory_data_source
from openmethane_prior.lib.sector.au_sector import AustraliaPriorSector

from .emission_sources.all_sources import all_emission_sources

logger = logger.get_logger(__name__)

def process_emissions(sector: AustraliaPriorSector, sector_config: PriorSectorConfig, prior_ds: xr.Dataset):
    config = sector_config.prior_config

    # read the total emissions over the sector (in kg)
    emissions_inventory = sector_config.data_manager.get_asset(inventory_data_source).data
    sector_total_emissions = get_sector_emissions_by_code(
        emissions_inventory=emissions_inventory,
        start_date=config.start_date,
        end_date=config.end_date,
        category_codes=sector.unfccc_categories,
    )

    # create a DataFrame with all potential methane emission sources in the sector
    emission_sources_df = all_emission_sources(
        data_manager=sector_config.data_manager,
        prior_config=config,
    )

    # emission sources don't include a methane quantity or proxy, so naively
    # distribute sector emissions evenly to each active petroleum well
    emission_sources_df["emissions_quantity"] = sector_total_emissions / len(emission_sources_df)

    domain_grid = config.domain_grid()

    methane = np.zeros(domain_grid.shape)

    for index, site in emission_sources_df.iterrows():
        # geometry type for each site will determine how to allocate emissions
        # to the grid
        geom_type = emission_sources_df.geom_type[index] if type(emission_sources_df.geom_type[index]) == str \
                    else emission_sources_df.geom_type[index].iloc[0]
        if geom_type == "Point":
            cell_x, cell_y, cell_valid = domain_grid.xy_to_cell_index(site["geometry"].x, site["geometry"].y)
            if cell_valid:
                methane[cell_y, cell_x] += site["emissions_quantity"]
        else:
            raise NotImplementedError("Allocating emissions to non-point geometry is not implemented")

    return kg_to_period_cell_flux(methane, config)


sector = AustraliaPriorSector(
    name="oil_gas",
    emission_category="anthropogenic",
    unfccc_categories=["1.B.2"], # Fugitive emissions from fuels, Oil and Natural Gas
    anzsic_codes=["07"], # Oil and Gas Extraction
    cf_standard_name="extraction_production_and_transport_of_fuel",
    create_estimate=process_emissions,
)
