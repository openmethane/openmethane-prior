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

from openmethane_prior.data_sources.inventory import (
    inventory_data_source,
    get_sector_emissions_by_code,
)
from openmethane_prior.lib import (
    DataSource,
    logger,
    PriorSector,
    PriorSectorConfig,
    regrid_data_array_conservative,
)
from openmethane_prior.lib.units import seconds_in_period

logger = logger.get_logger(__name__)

# "Agriculture Emissions Australia.nc" from the CSIRO collection "Methane
# Emissions in Melbourne, Australia: Prior Estimates using Global and National
# Data" v2, https://doi.org/10.25919/v3jn-7x24 (CC BY 4.0)
livestock_ch4_data_source = DataSource(
    name="csiro-livestock-ch4",
    url="https://data.csiro.au/dap/ws/v2/collections/75540/data/101166176",
    file_path="csiro-agriculture-emissions-australia-v2.nc",
)


def process_emissions(
    sector: PriorSector,
    sector_config: PriorSectorConfig,
    prior_ds: xr.Dataset,
):
    config = sector_config.prior_config
    domain_grid = config.domain().grid

    livestock_ch4_asset = sector_config.data_manager.get_asset(livestock_ch4_data_source)
    with xr.open_dataset(livestock_ch4_asset.path) as livestock_ch4_ds:
        livestock_ch4_da = livestock_ch4_ds["CH4"].load()

    # dataset values are kg/s per 0.01 degree cell, regridded to kg/s/m2
    livestock_regridded = regrid_data_array_conservative(
        data_da=livestock_ch4_da,
        domain_grid=domain_grid,
        cache_path=config.intermediates_path,
        cache_name=f"{livestock_ch4_asset.name}_{prior_ds.domain_name}",
        lat_dim="lat",
        lon_dim="lon",
        extensive=True,
    )
    livestock_np = livestock_regridded.values.astype(np.float64) * domain_grid.cell_area

    # the dataset is only used for its spatial distribution, the national
    # total comes from the inventory for the requested period
    emissions_inventory = sector_config.data_manager.get_asset(inventory_data_source).data
    total_emissions = get_sector_emissions_by_code(
        emissions_inventory=emissions_inventory,
        category_codes=sector.unfccc_categories,
        start_date=config.start_date,
        end_date=config.end_date,
    )
    logger.debug(f"Total emissions from livestock: {total_emissions / 1e6:.2f} kt")

    # normalise by the national total so emissions outside the domain are excluded
    source_total = livestock_ch4_da.sum(dtype=np.float64).item()
    ch4_np = total_emissions * livestock_np / source_total

    # convert CH4 kg to CH4 kg/s/m2
    return ch4_np / domain_grid.cell_area / seconds_in_period(config.start_date, config.end_date)


sector = PriorSector(
    name="livestock",
    emission_category="anthropogenic",
    unfccc_categories=[
        "3.A.1",  # Enteric Fermentation - Cattle
        "3.A.2",  # Enteric Fermentation - Sheep
        "3.B.1",  # Manure Management - Cattle
        "3.B.2",  # Manure Management - Sheep
    ],
    cf_standard_name="domesticated_livestock",
    create_estimate=process_emissions,
)
