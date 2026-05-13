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

"""Processing wetland emissions"""

import bisect
import calendar
import itertools
import logging
import os
import pathlib
import numpy as np
import xarray as xr
from shapely import geometry

from openmethane_prior.lib import (
    DataSource,
    Grid,
    PriorConfig,
    PriorSector,
    PriorSectorConfig,
    area_of_rectangle_m2,
    datetime64_to_datetime,
    load_zipped_pickle,
    redistribute_spatially,
    save_zipped_pickle,
)
from openmethane_prior.lib.data_manager.asset import DataAsset
from openmethane_prior.lib.units import SECONDS_PER_DAY

logger = logging.getLogger(__name__)

satwet_giems_data_source = DataSource(
    name="SatWet-GIEMS",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/SatWetCH4_GIEMS-MC_v2-90.nc",
)


def _build_regrid_indices(
    domain_grid: Grid,
    cache_path: pathlib.Path | str,
    cache_name: str,
    edge_lats: np.ndarray[tuple[int]],
    edge_lons: np.ndarray[tuple[int]],
) -> tuple[list, list, list]:
    """Load cached regridding indices or compute and cache them via Shapely polygon intersection."""
    cache_path = pathlib.Path(cache_path)
    indxPath = cache_path / f"{cache_name}_ind_x.p.gz"
    indyPath = cache_path / f"{cache_name}_ind_y.p.gz"
    coefsPath = cache_path / f"{cache_name}_ind_coefs.p.gz"

    if os.path.exists(indxPath) and os.path.exists(indyPath) and os.path.exists(coefsPath):
        return (
            load_zipped_pickle(indxPath),
            load_zipped_pickle(indyPath),
            load_zipped_pickle(coefsPath),
        )

    grid_shape = (len(edge_lons) - 1, len(edge_lats) - 1)
    cell_bounds_lon, cell_bounds_lat = domain_grid.cell_bounds_lonlat()

    ind_x = []
    ind_y = []
    coefs = []

    for i, j in itertools.product(range(domain_grid.shape[0]), range(domain_grid.shape[1])):
        IND_X = []
        IND_Y = []
        COEFS = []

        xvals = cell_bounds_lon[i, j]
        yvals = cell_bounds_lat[i, j]
        domain_grid_cell = geometry.Polygon(zip(xvals, yvals))

        ixminl = bisect.bisect_right(edge_lons, np.min(xvals))
        ixmaxr = bisect.bisect_right(edge_lons, np.max(xvals))
        iyminl = bisect.bisect_right(edge_lats, np.min(yvals))
        iymaxr = bisect.bisect_right(edge_lats, np.max(yvals))

        for ix, iy in itertools.product(
            range(max(0, ixminl - 1), min(grid_shape[0], ixmaxr)),
            range(max(0, iyminl - 1), min(grid_shape[1], iymaxr)),
        ):
            input_gridcell = geometry.box(
                edge_lons[ix],
                edge_lats[iy],
                edge_lons[ix + 1],
                edge_lats[iy + 1],
            )
            if domain_grid_cell.intersects(input_gridcell):
                intersection = domain_grid_cell.intersection(input_gridcell)
                input_cell_fraction = intersection.area / input_gridcell.area

                IND_X.append(ix)
                IND_Y.append(iy)
                COEFS.append(input_cell_fraction)

        ind_x.append(IND_X)
        ind_y.append(IND_Y)
        coefs.append(COEFS)

    save_zipped_pickle(ind_x, indxPath)
    save_zipped_pickle(ind_y, indyPath)
    save_zipped_pickle(coefs, coefsPath)

    return ind_x, ind_y, coefs


def regrid_satwet(
    config: PriorConfig,
    wetlands_da: DataAsset,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Regrid all SatWet time steps onto the domain grid.

    Returns raw flux values in original units (gCH4/m2/month) without any
    climatology averaging or unit conversion.

    Returns
    -------
    regridded : np.ndarray
        Shape (n_times, domain_y, domain_x), in gCH4/m2/month.
    satwet_times : np.ndarray
        The SatWet time coordinate (datetime64 array).
    """
    satwet_ds = xr.open_dataset(wetlands_da.path)
    domain_grid = config.domain_grid()

    latWetland = np.around(np.float64(satwet_ds["latitude"].values), 3)
    lonWetland = np.around(np.float64(satwet_ds["longitude"].values), 3)
    dlatWetland = latWetland[0] - latWetland[1]
    dlonWetland = lonWetland[1] - lonWetland[0]

    lonWetland_edge = np.zeros(len(lonWetland) + 1)
    lonWetland_edge[0:-1] = lonWetland - dlonWetland / 2.0
    lonWetland_edge[-1] = lonWetland[-1] + dlonWetland / 2.0
    lonWetland_edge = np.around(lonWetland_edge, 2)

    latWetland_edge = np.zeros(len(latWetland) + 1)
    latWetland_edge[0:-1] = latWetland + dlatWetland / 2.0
    latWetland_edge[-1] = latWetland[-1] - dlatWetland / 2.0
    latWetland_edge = np.around(latWetland_edge, 2)

    nlatWetland = len(latWetland)
    wetlandAreas = np.zeros((nlatWetland, len(lonWetland)))
    for iy in range(nlatWetland):
        wetlandAreas[iy, :] = (
                area_of_rectangle_m2(
                    latWetland_edge[iy],
                    latWetland_edge[iy + 1],
                    lonWetland_edge[0],
                    lonWetland_edge[-1],
                )
                / lonWetland.size
        )

    ind_x, ind_y, coefs = _build_regrid_indices(
        domain_grid=domain_grid,
        cache_name=wetlands_da.name,
        cache_path=config.intermediates_path,
        edge_lats=latWetland_edge,
        edge_lons=lonWetland_edge,
    )

    flux = satwet_ds["fch4_mean"].values
    satwet_times = satwet_ds["time"].values
    satwet_ds.close()

    cmaq_areas = np.ones(domain_grid.shape) * domain_grid.cell_area
    regridded = np.zeros((flux.shape[0], domain_grid.shape[0], domain_grid.shape[1]))
    for t_idx in range(flux.shape[0]):
        regridded[t_idx] = redistribute_spatially(
            domain_grid.shape, ind_x, ind_y, coefs, flux[t_idx], wetlandAreas, cmaq_areas
        )

    return regridded, satwet_times


def process_emissions(
    sector: PriorSector,
    sector_config: PriorSectorConfig,
    prior_ds: xr.Dataset,
):
    """Process wetland emissions for the given date range."""
    satwet_ch4_da = sector_config.data_manager.get_asset(satwet_giems_data_source)

    # Check if the requested period is covered by the SatWet dataset
    satwet_ds = xr.open_dataset(satwet_ch4_da.path)
    satwet_time = satwet_ds["time"].values
    satwet_ds.close()

    # SatWet time coordinates are first-of-month; compare at (year, month) granularity
    satwet_min_dt = datetime64_to_datetime(satwet_time.min())
    satwet_max_dt = datetime64_to_datetime(satwet_time.max())
    satwet_min_ym = (satwet_min_dt.year, satwet_min_dt.month)
    satwet_max_ym = (satwet_max_dt.year, satwet_max_dt.month)

    start_date = sector_config.prior_config.start_date
    end_date = sector_config.prior_config.end_date
    start_ym = (start_date.year, start_date.month)
    end_ym = (end_date.year, end_date.month)

    if start_ym < satwet_min_ym or end_ym > satwet_max_ym:
        logger.info(
            "Requested period %s - %s extends outside the SatWet data range %s - %s; "
            "monthly climatology will be used for out-of-range months.",
            start_date,
            end_date,
            satwet_min_dt,
            satwet_max_dt,
        )

    # Regrid all SatWet time steps to the domain grid (no unit conversion yet)
    regridded, satwet_times = regrid_satwet(sector_config.prior_config, satwet_ch4_da)

    # Convert units: gCH4/m2/month → kg/m2/s using the actual year+month per time step
    for t_idx, t in enumerate(satwet_times):
        dt = datetime64_to_datetime(t)
        _, days_in_month = calendar.monthrange(dt.year, dt.month)
        regridded[t_idx] /= 1000.0 * days_in_month * SECONDS_PER_DAY

    # Build (year, month) → index lookup for O(1) time-step selection
    satwet_index = {
        (datetime64_to_datetime(t).year, datetime64_to_datetime(t).month): i
        for i, t in enumerate(satwet_times)
    }

    # Compute monthly climatology (mean across all years per calendar month) for fallback
    monthly_climatology = {
        month: np.mean(
            regridded[[i for i, t in enumerate(satwet_times) if datetime64_to_datetime(t).month == month]],
            axis=0,
        )
        for month in range(1, 13)
    }

    # Select the matching SatWet time step (or climatology) for each prior_ds time coordinate
    domain_shape = sector_config.prior_config.domain_grid().shape
    result_nd = np.zeros((len(prior_ds["time"]), domain_shape[0], domain_shape[1]))

    for out_idx, date in enumerate(prior_ds["time"].values):
        dt = datetime64_to_datetime(date)
        ym = (dt.year, dt.month)
        if ym in satwet_index:
            result_nd[out_idx] = regridded[satwet_index[ym]]
        else:
            result_nd[out_idx] = monthly_climatology[dt.month]

    # source dataset is a coarse grid, and has emissions over ocean which
    # definitely shouldn't be classified as wetlands
    land_mask = prior_ds["land_mask"].to_numpy()
    result_nd *= land_mask

    result_nd = np.expand_dims(result_nd, 1)  # add single vertical dimension

    return xr.DataArray(
        result_nd,
        coords={
            "time": prior_ds["time"].values,
            "vertical": np.array([1]),
            "y": np.arange(result_nd.shape[-2]),
            "x": np.arange(result_nd.shape[-1]),
        },
    )


sector = PriorSector(
    name="wetlands",
    emission_category="natural",
    cf_standard_name="wetland_biological_processes",
    create_estimate=process_emissions,
)
