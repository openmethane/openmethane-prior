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
import hashlib
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

# degrees of longitude in half a turn
HALF_TURN = 180.0


def _compute_cell_edges(centres: np.ndarray) -> np.ndarray:
    """Compute cell-edge coordinates from cell-centre coordinates assuming uniform spacing."""
    d = centres[0] - centres[1]
    edges = np.zeros(len(centres) + 1)
    edges[:-1] = centres + d / 2.0
    edges[-1] = centres[-1] - d / 2.0
    # round away float noise, with enough precision for edges of 0.01 degree cells
    return np.around(edges, 6)


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


def _padded_cell_range(edges: np.ndarray, low: float, high: float) -> slice:
    """Index range of the cells spanning ``low`` to ``high``, plus one cell either side.

    ``edges`` must be ascending. The padding covers rounding in the cell edges.
    The range is clamped to the grid, so it is never empty.
    """
    n_cells = len(edges) - 1
    start = bisect.bisect_right(edges, low) - 1  # cell containing low
    stop = bisect.bisect_right(edges, high)  # one past the cell containing high
    return slice(max(0, start - 1), min(n_cells, stop + 1))


def _domain_cell_bounds_lonlat(
    domain_grid: Grid,
    lon_edges: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Corners of every domain cell in lon/lat, with longitudes in the source grid's range.

    Projections return longitudes between -180° and 180°, so a domain crossing
    the antimeridian would jump from 180° to -180°. The longitudes are made
    continuous across the domain instead, then shifted by whole turns to sit
    as close as possible to the source grid's longitudes, which may run from
    0° to 360°.
    """
    cell_bounds_lon, cell_bounds_lat = domain_grid.cell_bounds_lonlat()

    # bring every corner within half a turn of the centre cell, moving only
    # the corners that need it so the rest keep their exact values
    centre_lon = cell_bounds_lon[cell_bounds_lon.shape[0] // 2, cell_bounds_lon.shape[1] // 2, 0]
    from_centre = cell_bounds_lon - centre_lon
    cell_bounds_lon = np.where(from_centre > HALF_TURN, cell_bounds_lon - 360.0, cell_bounds_lon)
    cell_bounds_lon = np.where(from_centre < -HALF_TURN, cell_bounds_lon + 360.0, cell_bounds_lon)

    source_mid = (lon_edges[0] + lon_edges[-1]) / 2.0
    domain_mid = (cell_bounds_lon.min() + cell_bounds_lon.max()) / 2.0
    turns = np.round((source_mid - domain_mid) / 360.0)
    if turns:
        cell_bounds_lon = cell_bounds_lon + 360.0 * turns

    return cell_bounds_lon, cell_bounds_lat


def _domain_crop_slices(
    cell_bounds_lon: np.ndarray,
    cell_bounds_lat: np.ndarray,
    lat_edges: np.ndarray,
    lon_edges: np.ndarray,
) -> tuple[slice, list[tuple[slice, float]]]:
    """Index ranges of the source cells overlapping the domain.

    The bounding box covers the corners of every domain cell, not just the
    domain's corners, since the edges of a Lambert conformal domain curve in
    lon/lat.

    Returns the latitude range, and the longitude ranges in west-to-east order,
    each with the offset in degrees to add to its longitudes. A domain crossing
    the seam of a global source grid, where its longitudes wrap around, needs
    one range either side of the seam. The second range is shifted by a whole
    turn so it continues on from the first.
    """
    lon_min, lon_max = cell_bounds_lon.min(), cell_bounds_lon.max()
    lat_min, lat_max = cell_bounds_lat.min(), cell_bounds_lat.max()
    lat_range = _padded_cell_range(lat_edges, lat_min, lat_max)

    west, east = lon_edges[0], lon_edges[-1]
    # within half a cell of a full turn, allowing for rounding in the edges
    cell_width = (east - west) / (len(lon_edges) - 1)
    is_global = abs(east - west - 360.0) < cell_width / 2.0

    if not is_global or (west <= lon_min and lon_max <= east):
        return lat_range, [(_padded_cell_range(lon_edges, lon_min, lon_max), 0.0)]

    if lon_min < west:
        lon_ranges = [
            (_padded_cell_range(lon_edges, lon_min + 360.0, east), -360.0),
            (_padded_cell_range(lon_edges, west, lon_max), 0.0),
        ]
    else:
        lon_ranges = [
            (_padded_cell_range(lon_edges, lon_min, east), 0.0),
            (_padded_cell_range(lon_edges, west, lon_max - 360.0), 360.0),
        ]

    (first, _), (second, _) = lon_ranges
    if second.start < first.stop and first.start < second.stop:
        raise ValueError("Domain spans too much longitude to crop a global source grid")

    return lat_range, lon_ranges


def _source_grid_id(lat_edges: np.ndarray, lon_edges: np.ndarray) -> str:
    """Short hash identifying a source grid by its cell edges."""
    digest = hashlib.sha256(lat_edges.tobytes() + b"|" + lon_edges.tobytes())
    return digest.hexdigest()[:12]


def _build_weights(
    domain_grid: Grid,
    cell_bounds_lonlat: tuple[np.ndarray, np.ndarray],
    lat_edges: np.ndarray,
    lon_edges: np.ndarray,
    from_areas: np.ndarray,
) -> csr_array:
    """Build a sparse (n_out_cells, n_in_cells) weight matrix via Shapely polygon intersection.

    Each entry W[out, inp] = (fraction of input cell covered by output cell)
    * from_area[inp] / domain_grid.cell_area, so that W @ data.ravel() yields
    area-conserving regridded values in the same units as the input.

    ``cell_bounds_lonlat`` holds the lon and lat of the domain cells' corners,
    with longitudes in the same continuous range as ``lon_edges``.
    """
    n_lon = len(lon_edges) - 1
    n_lat = len(lat_edges) - 1
    n_out = domain_grid.shape[0] * domain_grid.shape[1]
    n_in = n_lat * n_lon

    cell_bounds_lon, cell_bounds_lat = cell_bounds_lonlat

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

    The source is first cropped to the cells overlapping the domain, so
    lazily opened data only reads that region from disk.

    Source longitudes may run from -180° to 180° or from 0° to 360°. A domain
    may cross the antimeridian, or the seam of a global source at 0°.

    The sparse weight matrix is computed on the first call and cached to disk;
    subsequent calls with the same ``cache_name`` and source grid load it
    directly.

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
    # bisect-based candidate search and the seam handling require ascending order
    data_da = data_da.sortby([lat_dim, lon_dim])

    lat_centres = np.around(np.float64(data_da[lat_dim].values), 3)
    lon_centres = np.around(np.float64(data_da[lon_dim].values), 3)
    lat_edges = _compute_cell_edges(lat_centres)
    lon_edges = _compute_cell_edges(lon_centres)

    cell_bounds_lon, cell_bounds_lat = _domain_cell_bounds_lonlat(domain_grid, lon_edges)

    # Crop before reading any values. Edges are sliced from the full grid
    # rather than recomputed, so they match the uncropped grid exactly.
    lat_slice, lon_ranges = _domain_crop_slices(
        cell_bounds_lon, cell_bounds_lat, lat_edges, lon_edges
    )
    lat_edges = lat_edges[lat_slice.start : lat_slice.stop + 1]

    # A domain across the seam of a global source has a range either side of
    # it. Joining them, with the second shifted a whole turn, gives a source
    # whose longitudes run continuously under the domain.
    pieces, piece_edges = [], []
    for lon_slice, offset in lon_ranges:
        piece = data_da.isel({lat_dim: lat_slice, lon_dim: lon_slice})
        if offset:
            piece = piece.assign_coords({lon_dim: piece[lon_dim] + offset})
        edges = lon_edges[lon_slice.start : lon_slice.stop + 1] + offset
        pieces.append(piece)
        # consecutive ranges share the edge at the seam
        piece_edges.append(edges if not piece_edges else edges[1:])
    data_da = pieces[0] if len(pieces) == 1 else xr.concat(pieces, dim=lon_dim)
    lon_edges = np.concatenate(piece_edges)

    # Weights index source cells by position, so they're only valid for the
    # (cropped) source grid they were built for.
    cache_path = pathlib.Path(cache_path)
    grid_id = _source_grid_id(lat_edges, lon_edges)
    cache_file = cache_path / f"{cache_name}_{grid_id}_weights.p.gz"

    if cache_file.exists():
        logger.info(f"Loading existing Grid weights for {cache_name}")
        W = load_zipped_pickle(cache_file)
    else:
        logger.info(f"No existing Grid weights for {cache_name}, calculating")
        from_areas = _compute_from_areas(lat_edges, lon_edges)
        W = _build_weights(
            domain_grid, (cell_bounds_lon, cell_bounds_lat), lat_edges, lon_edges, from_areas
        )
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
    flat = np.nan_to_num(flat, nan=0.0)
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
