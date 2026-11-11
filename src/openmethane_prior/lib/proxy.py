#
# Copyright 2026 The Superpower Institute Ltd.
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
from typing import Self

import attrs
import numpy as np
import pyproj
import shapely.ops
import xarray as xr
from shapely.geometry import MultiPolygon, Polygon

from openmethane_prior.lib.grid.domain import Domain
from openmethane_prior.lib.grid.geometry import grid_mask_from_polygon
from openmethane_prior.lib.grid.grid import Grid
from openmethane_prior.lib.grid.regrid import regrid_data
from openmethane_prior.lib.logger import get_logger
from openmethane_prior.lib.raster import remap_raster

logger = get_logger(__name__)


@attrs.frozen
class GriddedProxy:
    """A spatial proxy for emissions, gridded to two domains.

    A proxy such as night lights is gridded to both the prior domain and the
    inventory domain. An emission total for a region is distributed over the whole region in
    proportion to the proxy, so the prior domain receives only the share which
    falls inside it. The inventory domain covers every region in full, so it
    provides each region's proxy total even when the prior domain covers only
    part of the region.

    Both grids are masked to the inventory region, so cells outside it never
    receive emissions.
    """

    domain_grid: Grid
    """Grid of the prior domain"""

    domain_values: np.ndarray
    """Proxy values gridded to domain_grid"""

    inventory_grid: Grid
    """Grid of the inventory domain"""

    inventory_values: np.ndarray
    """Proxy values gridded to inventory_grid"""

    @classmethod
    def from_raster(
        cls,
        raster: xr.DataArray,
        domain_grid: Grid,
        inventory_domain: Domain,
        input_crs: pyproj.CRS | int = 4326,
    ) -> Self:
        """Grid a raster to the prior domain and the inventory domain.

        Both grids are masked to the inventory region.

        Parameters
        ----------
        raster
            Proxy raster with x and y coordinates in input_crs
        domain_grid
            Grid of the prior domain
        inventory_domain
            Inventory domain, which must include an ``inventory_mask`` variable
        input_crs
            Coordinate system of the raster
        """
        inventory_mask = np.asarray(inventory_domain.dataset["inventory_mask"])

        domain_values = remap_raster(raster, domain_grid, input_crs=input_crs)
        domain_values *= regrid_data(
            inventory_mask,
            from_grid=inventory_domain.grid,
            to_grid=domain_grid,
        )

        inventory_values = remap_raster(raster, inventory_domain.grid, input_crs=input_crs)
        inventory_values *= inventory_mask

        return cls(
            domain_grid=domain_grid,
            domain_values=domain_values,
            inventory_grid=inventory_domain.grid,
            inventory_values=inventory_values,
        )

    def distribute(
        self,
        total: float,
        region: Polygon | MultiPolygon | None = None,
    ) -> np.ndarray:
        """Distribute an emission total over a region by the proxy.

        The total is shared over the whole region in proportion to the proxy,
        and the share falling in each prior domain cell is returned.

        Parameters
        ----------
        total
            Emission total for the whole region
        region
            Shape of the region in the domain_grid coordinate system. If
            omitted, the total is distributed over the whole inventory region.

        Returns
        -------
        np.ndarray
            Emissions gridded to domain_grid. These sum to less than total
            when the prior domain covers only part of the region.
        """
        if region is None:
            domain_values = self.domain_values
            inventory_values = self.inventory_values
        else:
            domain_values = self.domain_values * grid_mask_from_polygon(self.domain_grid, region)
            inventory_region = self._to_inventory_crs(region)
            inventory_values = self.inventory_values * grid_mask_from_polygon(
                self.inventory_grid, inventory_region
            )

        region_total = inventory_values.sum()
        if region_total == 0:
            logger.warning(f"Proxy has no values in the region, unable to distribute {total}")
            return np.zeros(self.domain_grid.shape)

        return total * domain_values / region_total

    def _to_inventory_crs(self, region: Polygon | MultiPolygon) -> Polygon | MultiPolygon:
        domain_crs = self.domain_grid.projection.crs
        inventory_crs = self.inventory_grid.projection.crs
        if domain_crs.equals(inventory_crs):
            return region

        transformer = pyproj.Transformer.from_crs(domain_crs, inventory_crs, always_xy=True)
        return shapely.ops.transform(transformer.transform, region)
