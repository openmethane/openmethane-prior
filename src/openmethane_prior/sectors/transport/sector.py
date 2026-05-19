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

import xarray as xr

from openmethane_prior.data_sources.inventory import get_sector_emissions_by_code, inventory_data_source
from openmethane_prior.data_sources.nightlights import night_lights_data_source
from openmethane_prior.lib import (
    kg_to_period_cell_flux,
    logger,
    PriorSector,
    PriorParameters,
    DataManager,
)

logger = logger.get_logger(__name__)


def process_emissions(
    sector: PriorSector,
    params: PriorParameters, data_manager: DataManager,
    prior_ds: xr.Dataset,
):
    # we want proportions of total for scaling emissions
    om_ntlt_proportion = data_manager.get_asset(night_lights_data_source)

    # load the national inventory data, ready to calculate sectoral totals
    emissions_inventory = data_manager.get_asset(inventory_data_source).data
    sector_total_emissions = get_sector_emissions_by_code(
        emissions_inventory=emissions_inventory,
        start_date=params.start_date,
        end_date=params.end_date,
        category_codes=sector.unfccc_categories,
    )

    # allocate the proportion of the total to each grid cell
    sector_emissions = om_ntlt_proportion.data * sector_total_emissions

    return kg_to_period_cell_flux(sector_emissions, params)


sector = PriorSector(
    name="transport",
    emission_category="anthropogenic",
    unfccc_categories=["1.A.3"], # Transport
    cf_standard_name="land_transport",
    create_estimate=process_emissions,
)
