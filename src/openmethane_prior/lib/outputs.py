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
import numpy.typing as npt
import xarray as xr

from openmethane_prior.lib.config import PriorConfig
from openmethane_prior.lib.sector.sector import PriorSector
from openmethane_prior.lib.utils import SECS_PER_YEAR, get_version, get_timestamped_command, time_bounds, \
    list_cf_grid_mappings
import openmethane_prior.lib.logger as logger

logger = logger.get_logger(__name__)

COORD_NAMES = ["time", "vertical", "y", "x"]
# Dimensions used by sectors which produce a single estimate for the whole
# period, rather than one estimate per time step.
TIME_INVARIANT_COORD_NAMES = COORD_NAMES[1:]
COMMON_ATTRIBUTES = {
    "units": "kg/m2/s",
}
TOTAL_LAYER_NAME = "ch4_total"
TOTAL_LAYER_ATTRIBUTES = {
    "long_name": "total expected flux of methane based on public data",
    "standard_name": "surface_upward_mass_flux_of_methane",
}
SECTOR_PREFIX = "ch4_sector"

# Spatial extent of a single chunk of emissions data, in grid cells.
EMISSION_CHUNK_CELLS = 64
# Deflate level applied to compressed variables. Higher levels cost noticeably
# more time for less than 1MB on a month of output.
DEFLATE_LEVEL = 4


def emission_encoding(data_shape: tuple[int, ...]) -> dict:
    """
    Build the netCDF encoding used for every 4-dimensional emissions layer.

    Emissions layers are chunked so that a spatial tile holds every non-spatial
    step in one chunk, because the deflate filter can only collapse repeated
    values when the repeats share a chunk.

    Parameters
    ----------
    data_shape
        Shape of the emissions layer, in COORD_NAMES or
        TIME_INVARIANT_COORD_NAMES order.

    Returns
    -------
    :
        Encoding dict suitable for assigning to a DataArray's `encoding`.
    """
    *step_sizes, y_size, x_size = data_shape

    return {
        "zlib": True,
        # set explicitly: sector data derived from an input file inherits that
        # file's complevel, and complevel 0 silently disables compression
        "complevel": DEFLATE_LEVEL,
        # shuffle lets deflate find the repeated values in float data
        "shuffle": True,
        # domain variables arrive with contiguous storage, which netCDF cannot
        # combine with compression
        "contiguous": False,
        "chunksizes": (
            *step_sizes,
            min(EMISSION_CHUNK_CELLS, y_size),
            min(EMISSION_CHUNK_CELLS, x_size),
        ),
    }


def convert_to_timescale(emission, cell_area):
    """Convert a gridded emission dataset in kgs/cell/year to kgs/m2/s"""
    return emission / cell_area / SECS_PER_YEAR


def create_output_dataset(config: PriorConfig) -> xr.Dataset:
    domain_ds = config.domain().dataset
    period_start = config.start_date
    period_end = config.end_date

    # generate daily time steps
    time_steps = xr.date_range(start=period_start, end=period_end, freq="D", use_cftime=False, normalize=True)

    # find the domain variable containing the grid mapping
    grid_mapping_var = list_cf_grid_mappings(domain_ds)[0]
    
    # copy dimensions and attributes from the domain where the grid is defined
    prior_ds = xr.Dataset(
        coords={
            "x": domain_ds.coords["x"],
            "y": domain_ds.coords["y"],
            "time": (("time"), time_steps, {
                "standard_name": "time",
                "bounds": "time_bounds",
            }),
            # this dimension currently has no coordinate values, so it is left
            # as a dimension without coordinates
            # "vertical": (("vertical"), [0], {}),
        },
        data_vars={
            # meta data
            "lat": domain_ds["lat"],
            "lon": domain_ds["lon"],
            "x_bounds": domain_ds["x_bounds"],
            "y_bounds": domain_ds["y_bounds"],
            grid_mapping_var: domain_ds[grid_mapping_var],
            "cell_name": domain_ds["cell_name"],

            "time_bounds": (
                ("time", "time_period"),
                time_bounds(time_steps),
            ),

            # data variables
            "land_mask": domain_ds["land_mask"],

            # legacy / deprecated
            "LANDMASK": domain_ds["LANDMASK"],
        },
        attrs={
            # data attributes
            "DX": domain_ds.DX,
            "DY": domain_ds.DY,
            "XCELL": domain_ds.XCELL,
            "YCELL": domain_ds.YCELL,

            # domain
            "domain_name": domain_ds.domain_name,
            "domain_version": domain_ds.domain_version,
            "domain_slug": domain_ds.domain_slug,

            # meta attributes
            "title": "Open Methane prior emissions estimate",
            "comment": "Gridded prior emissions estimate for methane across Australia",
            "history": get_timestamped_command(),
            "openmethane_prior_version": get_version(),

            "Conventions": "CF-1.12",
        },
    )

    # ensure time and time_bounds use the same time encoding
    time_encoding = f"days since {period_start.strftime('%Y-%m-%d')}"
    prior_ds.time.encoding["units"] = time_encoding
    prior_ds.time_bounds.encoding["units"] = time_encoding

    # compress cell_names which take a lot of space
    prior_ds.cell_name.encoding["zlib"] = True

    # Grid metadata is copied from the domain file, which stores it
    # uncompressed. It is fixed in size, but large enough to dominate the
    # output once the emissions layers are compressed.
    for var_name in ["lat", "lon", "land_mask", "LANDMASK"]:
        prior_ds[var_name].encoding.update(
            {
                "zlib": True,
                # the domain file stores these with complevel 0, which would
                # leave them uncompressed even with zlib enabled
                "complevel": DEFLATE_LEVEL,
                "shuffle": True,
                # domain variables arrive with contiguous storage, which netCDF
                # cannot combine with compression
                "contiguous": False,
            }
        )

    # land_mask only ever holds 0 or 1, so a full int64 per cell is wasteful.
    prior_ds.land_mask.encoding["dtype"] = "int8"

    # disable _FillValue for variables that shouldn't have empty values
    for var_name in ['time_bounds', 'x', 'y', 'x_bounds', 'y_bounds', 'lat', 'lon']:
        prior_ds[var_name].encoding["_FillValue"] = None

    return prior_ds


def add_sector(
    prior_ds: xr.Dataset,
    sector_data: xr.DataArray | npt.ArrayLike,
    sector_meta: PriorSector,
):
    """
    Write a layer to the output file

    Parameters
    ----------
    prior_ds
        DataSet where sector data should be added
    sector_data
        Data to add to the output file
    sector_meta
        Name and meta details of the sector being added to the output
    """
    logger.info(f"Adding emissions data for {sector_meta.name}")

    if isinstance(sector_data, xr.DataArray) and "time" in sector_data.dims:
        # verify that time steps for the sector data match the parent coordinates exactly
        for time_step in sector_data.coords["time"].values:
            if time_step not in prior_ds.coords["time"].values:
                raise ValueError(f"Layer {sector_meta.name} time step {time_step} not found in dataset")

        sector_data = xr.DataArray(dims=COORD_NAMES[:], data=sector_data.values)
    elif np.ndim(sector_data) == len(COORD_NAMES):
        # already resolved per time step, but with no coords to verify against
        sector_data = xr.DataArray(dims=COORD_NAMES[:], data=np.asarray(sector_data))
    else:
        # Most sectors produce a single estimate covering the whole period.
        # That estimate is stored once, without a time dimension, rather than
        # repeated for every time step; consumers broadcast it across time when
        # combining it with the time-resolved layers.
        sector_data = xr.DataArray(
            dims=TIME_INVARIANT_COORD_NAMES[:],
            data=expand_sector_dims(sector_data),
        )

    # Convert masked arrays and NaN values to zero so sector outputs are clean
    raw = sector_data.values
    if isinstance(raw, np.ma.MaskedArray):
        raw = raw.filled(0)

    # Outputs shouldn't include an NaN values, replace NaN with zeroes
    raw = np.nan_to_num(raw, nan=0.0)
    sector_data = sector_data.copy(data=raw)

    # enable compression for layer data variables
    sector_data.encoding.update(emission_encoding(sector_data.shape))

    # find the domain variable containing the grid mapping
    grid_mapping_var = list_cf_grid_mappings(prior_ds)[0]

    sector_data.attrs = COMMON_ATTRIBUTES | {
        "standard_name": TOTAL_LAYER_ATTRIBUTES["standard_name"],
        "long_name": sector_meta.cf_long_name or f"expected flux of methane caused by sector: {sector_meta.name}",
        "emission_category": sector_meta.emission_category,
        "grid_mapping": grid_mapping_var,
    }
    if sector_meta.unfccc_categories is not None:
        sector_data.attrs["unfccc_categories"] = sector_meta.unfccc_categories
    if sector_meta.cf_standard_name is not None:
        sector_data.attrs["standard_name"] += f"_due_to_emission_from_{sector_meta.cf_standard_name}"

    _, aligned_sector_data = xr.align(prior_ds, sector_data, join="override")

    sector_var_name = f"{SECTOR_PREFIX}_{sector_meta.name}"
    prior_ds[sector_var_name] = aligned_sector_data

    return prior_ds


def expand_sector_dims(sector_data: xr.DataArray | npt.ArrayLike):
    """
    Expand layer data to use the spatial dimensions shared by every layer.

    Most layers produce 2-dimensional data, which must be expanded to include a
    "vertical" dimension with a single value. Such layers hold one estimate for
    the whole period and are stored without a time dimension, so no time
    expansion happens here.

    Parameters
    ----------
    sector_data
        Layer data with either ("y", "x") or ("vertical", "y", "x") dimensions.

    Returns
    -------
    :
        The data with ("vertical", "y", "x") dimensions.
    """
    if sector_data.ndim < 2:
        raise ValueError("expand_sector_dims supports a minimum of 2 dimensions")

    if sector_data.ndim > len(TIME_INVARIANT_COORD_NAMES):
        raise ValueError(
            "expand_sector_dims supports a maximum of "
            f"{len(TIME_INVARIANT_COORD_NAMES)} dimensions"
        )

    # we're about to alter the input so copy first
    copy = sector_data.copy()

    if copy.ndim == 2:
        # add single-value "vertical" layer
        copy = np.expand_dims(copy, axis=0)

    return copy


def add_ch4_total(prior_ds: xr.Dataset):
    """
    Calculate the total methane emissions from the individual layers and write to the output file.

    This adds the `ch4_total` variable to the output dataset.
    """
    # find the domain variable containing the grid mapping
    grid_mapping_var = list_cf_grid_mappings(prior_ds)[0]

    sectors = [var_name for var_name in prior_ds.data_vars.keys() if var_name.startswith(SECTOR_PREFIX)]

    # Sectors are stored either with or without a time dimension, so let xarray
    # broadcast the time-invariant ones across time as they are accumulated.
    total = None
    for sector_name in sectors:
        sector_data = prior_ds[sector_name]
        total = sector_data if total is None else total + sector_data

    if total is not None:
        # the total is always reported per time step, even when every
        # contributing sector was constant across the period
        if "time" not in total.dims:
            total = total.expand_dims(time=prior_ds.sizes["time"])

        summed = total.transpose(*COORD_NAMES).values

        prior_ds[TOTAL_LAYER_NAME] = (
            COORD_NAMES[:],
            summed,
            COMMON_ATTRIBUTES | TOTAL_LAYER_ATTRIBUTES | {
                "grid_mapping": grid_mapping_var,
            }
        )

        # enable compression for total layer which may be duplicated
        # across time steps
        prior_ds[TOTAL_LAYER_NAME].encoding.update(
            emission_encoding(prior_ds[TOTAL_LAYER_NAME].shape)
        )

        # Ensure legacy / deprecated "OCH4_TOTAL" layer is still in the output
        # until downstream consumers can be updated
        prior_ds["OCH4_TOTAL"] = (
            COORD_NAMES[:],
            summed,
            COMMON_ATTRIBUTES | TOTAL_LAYER_ATTRIBUTES | {
                "deprecated": "This variable is deprecated and will be removed in future versions",
                "superseded_by": TOTAL_LAYER_NAME
            }
        )
