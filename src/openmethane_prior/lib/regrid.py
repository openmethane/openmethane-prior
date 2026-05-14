#
# Copyright 2026 The Superpower Institute Ltd.
#
# This file is part of Open Methane.
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

"""Area-weighted regridding of geospatial datasets onto the domain grid."""

import bisect
import itertools
import pathlib
import numpy as np
import xarray as xr
from scipy.sparse import csr_array
from shapely import geometry

from .grid.grid import Grid
from .logger import get_logger
from .utils import area_of_rectangle_m2, load_zipped_pickle, save_zipped_pickle

logger = get_logger(__name__)


def _compute_cell_edges(centres: np.ndarray) -> np.ndarray:
    """Compute cell-edge coordinates from cell-centre coordinates assuming uniform spacing."""
    d = centres[0] - centres[1]
    edges = np.zeros(len(centres) + 1)
    edges[:-1] = centres + d / 2.0
    edges[-1] = centres[-1] - d / 2.0
    return np.around(edges, 2)


def _compute_from_areas(lat_edges: np.ndarray, lon_edges: np.ndarray) -> np.ndarray:
    """Compute grid-cell areas in m² for a regular lat/lon grid (ascending lat_edges)."""
    n_lat = len(lat_edges) - 1
    n_lon = len(lon_edges) - 1
    areas = np.zeros((n_lat, n_lon))
    for iy in range(n_lat):
        areas[iy, :] = (
            area_of_rectangle_m2(lat_edges[iy], lat_edges[iy + 1], lon_edges[0], lon_edges[-1])
            / n_lon
        )
    return areas


def _build_weights(
    domain_grid: Grid,
    lat_edges: np.ndarray,
    lon_edges: np.ndarray,
    from_areas: np.ndarray,
) -> csr_array:
    """Build a sparse (n_out_cells, n_in_cells) weight matrix via Shapely polygon intersection.

    Each entry W[out, inp] = (fraction of input cell covered by output cell)
    * from_area[inp] / domain_grid.cell_area, so that W @ data.ravel() yields
    area-conserving regridded values in the same units as the input.
    """
    n_lon = len(lon_edges) - 1
    n_lat = len(lat_edges) - 1
    n_out = domain_grid.shape[0] * domain_grid.shape[1]
    n_in = n_lat * n_lon

    cell_bounds_lon, cell_bounds_lat = domain_grid.cell_bounds_lonlat()

    rows, cols, data = [], [], []

    for i, j in itertools.product(range(domain_grid.shape[0]), range(domain_grid.shape[1])):
        ij = i * domain_grid.shape[1] + j
        xvals = cell_bounds_lon[i, j]
        yvals = cell_bounds_lat[i, j]
        domain_cell = geometry.Polygon(zip(xvals, yvals))

        ixminl = bisect.bisect_right(lon_edges, np.min(xvals))
        ixmaxr = bisect.bisect_right(lon_edges, np.max(xvals))
        iyminl = bisect.bisect_right(lat_edges, np.min(yvals))
        iymaxr = bisect.bisect_right(lat_edges, np.max(yvals))

        for ix, iy in itertools.product(
            range(max(0, ixminl - 1), min(n_lon, ixmaxr)),
            range(max(0, iyminl - 1), min(n_lat, iymaxr)),
        ):
            input_cell = geometry.box(
                lon_edges[ix], lat_edges[iy], lon_edges[ix + 1], lat_edges[iy + 1]
            )
            if domain_cell.intersects(input_cell):
                intersection = domain_cell.intersection(input_cell)
                coef = intersection.area / input_cell.area
                rows.append(ij)
                cols.append(iy * n_lon + ix)
                data.append(coef * from_areas[iy, ix] / domain_grid.cell_area)

    return csr_array((data, (rows, cols)), shape=(n_out, n_in))


def regrid_data_array_conservative(
    data_da: xr.DataArray,
    domain_grid: Grid,
    cache_path: pathlib.Path,
    cache_name: str,
    lat_dim: str = "latitude",
    lon_dim: str = "longitude",
    extensive: bool = False,
) -> xr.DataArray:
    """Regrid a DataArray onto the domain grid using area-weighted interpolation.

    The sparse weight matrix is computed on the first call and cached to disk;
    subsequent calls with the same ``cache_name`` load it directly.

    Parameters
    ----------
    data_da
        Input data. The last two dimensions must be ``lat_dim`` and ``lon_dim``
        (in any order); all leading dimensions and coordinates are preserved.
    domain_grid
        Target domain grid.
    cache_path
        Directory in which to save/load the sparse weight matrix.
    cache_name
        Unique identifier used to name the cache file. Using a combination of
        data asset name and domain name is recommended.
    lat_dim
        Name of the latitude dimension in ``data_da``.
    lon_dim
        Name of the longitude dimension in ``data_da``.
    extensive
        If ``True``, the input is treated as an extensive quantity (total per
        grid cell, e.g. Mt/cell). It is divided by source cell areas before
        regridding so that the weight matrix, which expects a density, receives
        the correct units. The output is then in the same per-m² units as a
        density input would produce.

    Returns
    -------
        DataArray with the same leading dimensions/coordinates as ``data_da``
        and spatial dimensions replaced by ``(y, x)`` on the domain grid.
    """
    cache_path = pathlib.Path(cache_path)
    cache_file = cache_path / f"{cache_name}_weights.p.gz"

    # bisect-based candidate search requires ascending lat order
    data_da = data_da.sortby(lat_dim)

    lat_centres = np.around(np.float64(data_da[lat_dim].values), 3)
    lon_centres = np.around(np.float64(data_da[lon_dim].values), 3)
    lat_edges = _compute_cell_edges(lat_centres)
    lon_edges = _compute_cell_edges(lon_centres)

    if cache_file.exists():
        logger.info(f"Loading existing Grid weights for {cache_name}")
        W = load_zipped_pickle(cache_file)
    else:
        logger.info(f"No existing Grid weights for {cache_name}, calculating")
        from_areas = _compute_from_areas(lat_edges, lon_edges)
        W = _build_weights(domain_grid, lat_edges, lon_edges, from_areas)
        save_zipped_pickle(W, cache_file)

    if extensive:
        from_areas = _compute_from_areas(lat_edges, lon_edges)
        area_da = xr.DataArray(
            from_areas,
            dims=[lat_dim, lon_dim],
            coords={lat_dim: data_da[lat_dim], lon_dim: data_da[lon_dim]},
        )
        data_da = data_da / area_da

    spatial_dims = {lat_dim, lon_dim}
    leading_dims = [d for d in data_da.dims if d not in spatial_dims]

    data_da = data_da.transpose(*leading_dims, lat_dim, lon_dim)

    values = data_da.values.astype(np.float64)
    n_lat, n_lon = values.shape[-2], values.shape[-1]
    leading_shape = values.shape[:-2]

    flat = values.reshape(-1, n_lat * n_lon)
    regridded = (W @ flat.T).T.reshape(*leading_shape, *domain_grid.shape)

    leading_coords = {d: data_da[d].values for d in leading_dims if d in data_da.coords}

    return xr.DataArray(
        regridded.astype(np.float32),
        dims=[*leading_dims, "y", "x"],
        coords={
            **leading_coords,
            "y": np.arange(domain_grid.shape[0]),
            "x": np.arange(domain_grid.shape[1]),
        },
    )
