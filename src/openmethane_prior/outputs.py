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

from openmethane_prior.config import PriorConfig
from openmethane_prior.utils import SECS_PER_YEAR, extract_bounds, get_version, get_timestamped_command, time_bounds

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


def create_output_dataset(
    config: PriorConfig,
    start_date: datetime.date,
    end_date: datetime.date,
) -> xr.Dataset:
    domain_ds = config.domain_dataset()
    period_start = start_date
    period_end = end_date

    # create a variable with projection coordinates
    projection_x = (
        domain_ds.XORIG + (0.5 * domain_ds.XCELL)
        + np.arange(len(domain_ds.COL)) * domain_ds.XCELL
    )

    projection_y = (
        domain_ds.YORIG + (0.5 * domain_ds.YCELL)
        + np.arange(len(domain_ds.ROW)) * domain_ds.YCELL
    )

    # generate daily time steps
    time_steps = xr.date_range(start=period_start, end=period_end, freq="D", use_cftime=True, normalize=True)

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
                    "bounds": "lat_bounds",
                },
            ),
            "lon": (
                ("y", "x"),
                domain_ds.variables["LON"].squeeze(),
                {
                    "long_name": "longitude coordinate",
                    "units": "degrees_east",
                    "standard_name": "longitude",
                    "bounds": "lon_bounds",
                },
            ),

            # https://cfconventions.org/Data/cf-conventions/cf-conventions-1.11/cf-conventions.html#cell-boundaries
            "lat_bounds": extract_bounds(domain_ds.variables["LATD"].squeeze()),
            "lon_bounds": extract_bounds(domain_ds.variables["LOND"].squeeze()),

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
            "projection_x": (
                ("x"),
                projection_x,
                {
                    "long_name": "x coordinate of projection",
                    "units": "m",
                    "standard_name": "projection_x_coordinate",
                },
            ),
            "projection_y": (
                ("y"),
                projection_y,
                {
                    "long_name": "y coordinate of projection",
                    "units": "m",
                    "standard_name": "projection_y_coordinate",
                },
            ),
            "time_bounds": (
                ("time", "time_period"),
                time_bounds(time_steps),
            ),

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
            "x": domain_ds.coords["COL"].values,
            "y": domain_ds.coords["ROW"].values,
            "time": (("time"), time_steps, {
                "bounds": "time_bounds",
            }),
        },
        attrs={
            "DX": domain_ds.DX,
            "DY": domain_ds.DY,
            "XCELL": domain_ds.XCELL,
            "YCELL": domain_ds.YCELL,
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

    return prior_ds


def initialise_output(
    config: PriorConfig,
    start_date: datetime.date,
    end_date: datetime.date,
):
    """
    Initialise the output directory

    Copies the input domain to the output domain

    Parameters
    ----------
    config
        Configuration object
    """
    config.output_domain_file.parent.mkdir(parents=True, exist_ok=True)

    output_ds = create_output_dataset(config, start_date, end_date)
    output_ds.to_netcdf(config.output_domain_file)


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

    sector_var_name = f"{SECTOR_PREFIX}_{sector_name}"
    ds[sector_var_name] = sector_data

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
