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
"""Output handling"""
import datetime
import pathlib

import numpy as np
import numpy.typing as npt
import xarray as xr

from openmethane_prior.cell_name import encode_grid_cell_name
from openmethane_prior.config import PriorConfig, PublishedInputDomain
from openmethane_prior.utils import SECS_PER_YEAR, get_version, get_timestamped_command, time_bounds, \
    bounds_from_cell_edges

COORD_NAMES = ["time", "vertical", "y", "x"]
PROJECTION_VAR_NAME = "lambert_conformal"
COMMON_ATTRIBUTES = {
    "grid_mapping": PROJECTION_VAR_NAME,
    "units": "kg/m2/s",
}
TOTAL_LAYER_NAME = "ch4_total"
TOTAL_LAYER_ATTRIBUTES = {
    "long_name": "total expected flux of methane based on public data",
    "standard_name": "surface_upward_mass_flux_of_methane",
}
SECTOR_PREFIX = "ch4_sector"


def convert_to_timescale(emission, cell_area):
    """Convert a gridded emission dataset in kgs/cell/year to kgs/m2/s"""
    return emission / cell_area / SECS_PER_YEAR


def create_output_dataset(config: PriorConfig) -> xr.Dataset:
    domain_ds = config.domain_dataset()
    domain_grid = config.domain_grid()
    period_start = config.start_date
    period_end = config.end_date

    # generate daily time steps
    time_steps = xr.date_range(start=period_start, end=period_end, freq="D", use_cftime=True, normalize=True)

    # generate grid cell names
    # TODO: generate and store these when creating the domain file
    grid_cell_names = []
    for y in range(domain_grid.shape[0]):
        grid_cell_names.append([])
        for x in range(domain_grid.shape[1]):
            grid_cell_names[-1].append(encode_grid_cell_name(config.input_domain.slug, x, y, "."))

    # copy dimensions and attributes from the domain where the grid is defined
    prior_ds = xr.Dataset(
        data_vars={
            # meta data
            "lat": (
                ("y", "x"),
                domain_ds.variables["LAT"].squeeze(),
                {
                    "long_name": "latitude coordinate",
                    "units": "degrees_north",
                    "standard_name": "latitude",
                },
            ),
            "lon": (
                ("y", "x"),
                domain_ds.variables["LON"].squeeze(),
                {
                    "long_name": "longitude coordinate",
                    "units": "degrees_east",
                    "standard_name": "longitude",
                },
            ),

            # # https://cfconventions.org/Data/cf-conventions/cf-conventions-1.11/cf-conventions.html#cell-boundaries
            "x_bounds": (("x", "cell_bounds"), bounds_from_cell_edges(domain_grid.cell_bounds_x())),
            "y_bounds": (("y", "cell_bounds"), bounds_from_cell_edges(domain_grid.cell_bounds_y())),

            # https://cfconventions.org/Data/cf-conventions/cf-conventions-1.11/cf-conventions.html#_lambert_conformal
            PROJECTION_VAR_NAME: (
                (),
                0,
                {
                    "grid_mapping_name": "lambert_conformal_conic",
                    "standard_parallel": (domain_ds.TRUELAT1, domain_ds.TRUELAT2),
                    "longitude_of_central_meridian": domain_ds.STAND_LON,
                    "latitude_of_projection_origin": domain_ds.MOAD_CEN_LAT,
                    "proj4": config.domain_projection().to_proj4(),
                },
            ),
            "time_bounds": (
                ("time", "time_period"),
                time_bounds(time_steps),
            ),
            "cell_name": (("y", "x"), grid_cell_names, {
                "long_name": "unique grid cell name",
            }),

            # data variables
            "land_mask": (
                ("y", "x"),
                domain_ds.variables["LANDMASK"].squeeze().astype(int),
                {
                    "standard_name": "land_binary_mask",
                    "units": "1",
                    "long_name": "land-water mask (1=land, 0=water)",
                },
            ),

            # legacy / deprecated
            "LANDMASK": (
                ("y", "x"),
                domain_ds.variables["LANDMASK"].squeeze(),
                domain_ds.variables["LANDMASK"].attrs,
            ),
        },
        coords={
            "x": (("x"), domain_grid.cell_coords_x(), {
                "long_name": "x coordinate of projection",
                "units": "m",
                "standard_name": "projection_x_coordinate",
                "bounds": "x_bounds",
            }),
            "y": (("y"), domain_grid.cell_coords_y(), {
                "long_name": "y coordinate of projection",
                "units": "m",
                "standard_name": "projection_y_coordinate",
                "bounds": "y_bounds",
            }),
            "time": (("time"), time_steps, {
                "standard_name": "time",
                "bounds": "time_bounds",
            }),
            # this dimension currently has no coordinate values, so it is left
            # as a dimension without coordinates
            # "vertical": (("vertical"), [0], {}),
        },
        attrs={
            # data attributes
            "DX": domain_ds.DX,
            "DY": domain_ds.DY,
            "XCELL": domain_ds.XCELL,
            "YCELL": domain_ds.YCELL,

            # domain
            "domain_name": config.input_domain.name,
            "domain_version": config.input_domain.version,
            "domain_slug": config.input_domain.slug,

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

    return prior_ds


def initialise_output(config: PriorConfig):
    """
    Initialise the output directory

    Copies the input domain to the output domain

    Parameters
    ----------
    config
        Configuration object
    """
    config.output_file.parent.mkdir(parents=True, exist_ok=True)

    output_ds = create_output_dataset(config)
    output_ds.to_netcdf(config.output_file)


def write_sector(
    output_path: pathlib.Path,
    sector_name: str,
    sector_data: xr.DataArray | npt.ArrayLike,
    sector_standard_name: str = None,
    sector_long_name: str = None,
):
    """
    Write a layer to the output file

    Parameters
    ----------
    output_path
        Path to the output file.

        This file should already exist and will be updated to include the layer data
    sector_name
        Name
    sector_data
        Data to write to file

        This could be a xarray Dataset
    direct_set
        If True, write the data to the output file without processing
        If False, coerce to the sector_data to 4d if it isn't already
    """
    print(f"Writing emissions data for {sector_name}")

    if not output_path.exists():
        raise FileNotFoundError(f"Output domain file not found: {output_path}")

    ds = xr.load_dataset(output_path)

    # determine the expected shape of a data layer based on the assumed coords
    expected_shape = tuple([(ds.sizes[coord_name] if coord_name in ds.sizes else 1) for coord_name in COORD_NAMES])

    # if this is a DataArray with the right dimensions, it can be added directly
    if type(sector_data) == xr.DataArray and sector_data.shape == expected_shape:
        # verify that time steps for the sector data match the parent coordinates exactly
        for time_step in sector_data.coords["time"].values:
            if time_step not in ds.coords["time"].values:
                raise ValueError(f"Layer {sector_name} time step {time_step} not found in dataset")
    else:
        # some layers only generate 2 or 3-dimensional data, which needs
        # to be expanded into the same dimensions as the other layers
        sector_data = xr.DataArray(
            dims=COORD_NAMES[:],
            data=expand_sector_dims(sector_data, ds.sizes["time"]),
        )

        # enable compression for expanded layer data which may be duplicated
        # across time steps
        sector_data.encoding["zlib"] = True

    sector_data.attrs = COMMON_ATTRIBUTES | {
        "standard_name": TOTAL_LAYER_ATTRIBUTES["standard_name"],
        "long_name": sector_long_name or f"expected flux of methane caused by sector: {sector_name}",
    }
    if sector_standard_name is not None:
        sector_data.attrs["standard_name"] += f"_due_to_emission_from_{sector_standard_name}"

    _, aligned_sector_data = xr.align(ds, sector_data, join="override")

    sector_var_name = f"{SECTOR_PREFIX}_{sector_name}"
    ds[sector_var_name] = aligned_sector_data

    ds.to_netcdf(output_path)


def expand_sector_dims(
    sector_data: xr.DataArray | npt.ArrayLike,
    time_steps: int | None = 1,
):
    """
    Expands layer data to use the same dimensions as other spatial layers.
    Most layers produce 2-dimensional data, which must be expanded to include:
    - "vertical" dimension with a single value
    - "time" dimension, which must match the size of the existing time dim

    When expanding the time dim, we are working with datasets that produce a
    single average emission across the entire period, so we just duplicate it
    across all the periods present in the output.

    :param sector_data:
    :param time_steps:
    :return:
    """
    if sector_data.ndim < 2:
        raise ValueError("expand_sector_dims supports a minimum of 2 dimensions")

    # we're about to alter the input so copy first
    copy = sector_data.copy()

    if copy.ndim == 2:
        # add single-value "vertical" layer
        copy = np.expand_dims(copy, axis=0)

    if copy.ndim == 3:
        # add single-value "time" layer
        copy = np.expand_dims(copy, axis=0)

    if copy.ndim == 4 and copy.shape[0] < time_steps:
        # duplicate the existing data across as many time steps are required
        # see: https://stackoverflow.com/questions/39463019/how-to-copy-numpy-array-value-into-higher-dimensions/55754233#55754233
        copy = np.concatenate([copy] * time_steps, axis=0)

    return copy


def sum_sectors(output_path: pathlib.Path):
    """
    Calculate the total methane emissions from the individual layers and write to the output file.

    This adds the `ch4_total` variable to the output file.
    """
    if not output_path.exists():
        raise FileNotFoundError("Output file does not exist")

    ds = xr.load_dataset(output_path)

    sectors = [var_name for var_name in ds.data_vars.keys() if var_name.startswith(SECTOR_PREFIX)]

    # now check to find largest shape because we'll broadcast everything else to that
    summed = None
    for sector_name in sectors:
        if summed is None:
            # all sectors should have dims normalised by expand_sector_dims, so
            # if this is the first layer, simply copy it
            summed = np.zeros(ds[sector_name].shape)

        # add each layer to the accumulated sum
        summed += ds[sector_name].values

    if summed is not None:
        ds[TOTAL_LAYER_NAME] = (
            COORD_NAMES[:],
            summed,
            COMMON_ATTRIBUTES | TOTAL_LAYER_ATTRIBUTES
        )

        # enable compression for total layer which may be duplicated
        # across time steps
        ds[TOTAL_LAYER_NAME].encoding["zlib"] = True

        # Ensure legacy / deprecated "OCH4_TOTAL" layer is still in the output
        # until downstream consumers can be updated
        ds["OCH4_TOTAL"] = (
            COORD_NAMES[:],
            summed,
            COMMON_ATTRIBUTES | TOTAL_LAYER_ATTRIBUTES | {
                "deprecated": "This variable is deprecated and will be removed in future versions",
                "superseded_by": TOTAL_LAYER_NAME
            }
        )

        ds.to_netcdf(output_path)
