#!/usr/bin/env python
#
# Copyright 2023 The Superpower Institute Ltd.
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

"""
Generate domain file for use by Open Methane prior and alerts.

The generated file is based on the WRF Geometry file and then is subset to
match the CMAQ domain. The domain for Open Methane is a combination of the WRF
domain as specified in the setup-wrf repo and the value of BTRIM for the CMAQ
domain (namely in MCIP).

Each domain file has a domain name and version associated with it. The version
can be anything, but we recommend a simple, serial increment like v1, v2, etc.

This only needs to be run once for each new domain/modification.
"""

import os
import pathlib

import click
import numpy as np
import rasterio
import rioxarray as rxr
import xarray as xr

from openmethane_prior.cell_name import encode_grid_cell_name
from openmethane_prior.grid.create_grid import create_grid_from_mcip
from openmethane_prior.raster import remap_raster
from openmethane_prior.utils import bounds_from_cell_edges, get_timestamped_command, get_version
import openmethane_prior.logger as logger

logger = logger.get_logger(__name__)

PROJECTION_VAR_NAME = "lambert_conformal"

def create_domain_info(
    geometry_file: pathlib.Path,
    cross_file: pathlib.Path,
    landuse_file: pathlib.Path,
    domain_name: str,
    domain_version: str,
    domain_index: int,
    domain_slug: str,
) -> xr.Dataset:
    """
    Create a new domain from the input WRF domain, subset to match the CMAQ
    domain. An "inventory mask" is added to represent all locations that will
    be considered within the political or geographic boundary where public
    emission estimates will be available to allocate within the domain.

    :param geometry_file: Path to the WRF geometry file
    :param cross_file: Path to the MCIP cross file
    :param landuse_file: Path to the land use GeoTIFF
    :param domain_name: The name of the new domain
    :param domain_version: The version of the domain being generated
    :param domain_index: The subdomain index
    :param domain_slug: A short, URL-safe name for the domain
    :return: The re-gridded domain information as an xarray Dataset
    """
    geom_xr = xr.open_dataset(geometry_file)
    mcip_cro_xr = xr.open_dataset(cross_file)

    domain_grid = create_grid_from_mcip(
        TRUELAT1=geom_xr.TRUELAT1,
        TRUELAT2=geom_xr.TRUELAT2,
        MOAD_CEN_LAT=geom_xr.MOAD_CEN_LAT,
        STAND_LON=geom_xr.STAND_LON,
        COLS=mcip_cro_xr.COL.size,
        ROWS=mcip_cro_xr.ROW.size,
        XCENT=mcip_cro_xr.XCENT,
        YCENT=mcip_cro_xr.YCENT,
        XORIG=mcip_cro_xr.XORIG,
        YORIG=mcip_cro_xr.YORIG,
        XCELL=mcip_cro_xr.XCELL,
        YCELL=mcip_cro_xr.YCELL,
    )

    logger.info("Creating domain dataset")

    # generate grid cell names
    grid_cell_names = []
    for y in range(domain_grid.shape[0]):
        grid_cell_names.append([])
        for x in range(domain_grid.shape[1]):
            grid_cell_names[-1].append(encode_grid_cell_name(domain_slug, x, y, "."))

    domain_ds = xr.Dataset(
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
        },
        data_vars={
            # meta data
            "lat": (
                ("y", "x"),
                mcip_cro_xr.variables["LAT"].squeeze(),
                {
                    "long_name": "latitude coordinate",
                    "units": "degrees_north",
                    "standard_name": "latitude",
                },
            ),
            "lon": (
                ("y", "x"),
                mcip_cro_xr.variables["LON"].squeeze(),
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
            PROJECTION_VAR_NAME: ((), 0, domain_grid.projection.crs.to_cf()),

            "cell_name": (("y", "x"), grid_cell_names, {
                "long_name": "unique grid cell name",
            }),

            # data variables
            "land_mask": (
                ("y", "x"),
                mcip_cro_xr.variables["LWMASK"].squeeze().astype(int),
                {
                    "standard_name": "land_binary_mask",
                    "units": "1",
                    "long_name": "land-water mask (1=land, 0=water)",
                    "grid_mapping": PROJECTION_VAR_NAME,
                },
            ),

            # legacy / deprecated
            "LANDMASK": (
                ("y", "x"),
                mcip_cro_xr.variables["LWMASK"].squeeze(),
                mcip_cro_xr.variables["LWMASK"].attrs,
            ),
        },
        attrs={
            # data attributes
            "DX": geom_xr.DX,
            "DY": geom_xr.DY,
            "XCELL": mcip_cro_xr.XCELL,
            "YCELL": mcip_cro_xr.YCELL,
            "XORIG": mcip_cro_xr.XORIG,
            "YORIG": mcip_cro_xr.YORIG,

            # domain
            "domain_name": domain_name,
            "domain_version": domain_version,
            "domain_index": domain_index,
            "domain_slug": domain_slug,

            # meta attributes
            "title": f"Open Methane domain: {domain_name}",
            "history": get_timestamped_command(),
            "openmethane_prior_version": get_version(),

            "Conventions": "CF-1.12",
        },
    )

    logger.info("Loading land use data to generate inventory mask")
    # this seems to need two approaches since rioxarray
    # seems to always convert to float which we don't want but we need it for the other tif attributes
    landuse_xr = rxr.open_rasterio(landuse_file, masked=True)
    lu_x = landuse_xr.x
    lu_y = landuse_xr.y
    lu_area = landuse_xr.AREA_OR_POINT
    lu_crs = landuse_xr.rio.crs
    landuse_xr.close()

    landuse_rio = rasterio.open(landuse_file,
        engine='rasterio',
    ).read()
    landuse_rio = landuse_rio.squeeze()
    landuse_rio[landuse_rio != 0] = 1 # now pure land-oc mask
    sector_xr = xr.DataArray(landuse_rio, coords={ 'y': lu_y, 'x': lu_x  })

    # now aggregate to coarser resolution of the domain grid
    inventory_mask = remap_raster(sector_xr, domain_grid, input_crs=lu_crs, AREA_OR_POINT=lu_area)

    # now count pixels in each coarse gridcell by aggregating array of 1
    landuse_rio[...] = 1
    count_mask = remap_raster(sector_xr, domain_grid, input_crs=lu_crs, AREA_OR_POINT=lu_area)
    has_vals = count_mask > 0
    inventory_mask[has_vals] /= count_mask[has_vals]
    # binary choice land or ocean
    inventory_mask = np.where( inventory_mask > 0.5, 1., 0.)

    domain_ds['inventory_mask'] = xr.DataArray(
        dims=('y', 'x'),
        data=inventory_mask,
        attrs={
            "units": "1",
            "long_name": "mask for inventories over domain",
            "grid_mapping": PROJECTION_VAR_NAME,
        },
    )

    return domain_ds


def write_domain_info(domain_ds: xr.Dataset, domain_path: pathlib.Path):
    """
    Write the domain information to a netcdf file

    Parameters
    ----------
    domain_ds
        The domain information as a xarray dataset
    domain_path
        The path to write the domain information to
    """
    print(f"Writing domain to {domain_path}")
    domain_path.parent.mkdir(parents=True, exist_ok=True)

    domain_ds.to_netcdf(domain_path)


def validate_mcip_path(required_content: str):
    def validator(ctx, param, value):
        path = pathlib.Path(value)

        # Existence of the file is checked by `click.Path`

        if not path.name.startswith(required_content):
            raise click.BadParameter(f"Filename must start with {required_content}")

        return pathlib.Path(value)

    return validator


def clean_directories(geometry_directory, output_directory, name, version):
    geometry_directory = pathlib.Path(geometry_directory)

    if output_directory is None:
        output_directory = geometry_directory
    else:
        output_directory = pathlib.Path(output_directory)

    if not geometry_directory.exists():
        raise click.BadParameter(
            f"WRF geometry for domain {name}@{version} does not exist. Check {geometry_directory}"
        )
    return geometry_directory, output_directory


@click.command(name="create_prior_domain")
@click.option(
    "--name",
    type=str,
    required=True,
    help="Name of the WRF domain",
    default=lambda: os.environ.get("DOMAIN_NAME"),
)
@click.option(
    "--version",
    type=str,
    required=True,
    help="Version identifier of the WRF domain. Must start with v",
    default=lambda: os.environ.get("DOMAIN_VERSION"),
)
@click.option(
    "--slug",
    type=str,
    required=False,
    help="Short, URL-safe name for the domain",
    default=lambda: os.environ.get("DOMAIN_SLUG", None),
)
@click.option(
    "--domain-index",
    type=int,
    default=1,
    help="Number of the domain to process (Currently we don't support nested domains)",
)
@click.option(
    "--cross",
    type=click.Path(exists=True, file_okay=True),
    callback=validate_mcip_path("GRIDCRO2D"),
    required=True,
    help="Path to the GRIDCRO2D file for the domain",
)
@click.option(
    "--landuse",
    type=click.Path(exists=True, file_okay=True),
    required=True,
    help="Path to the GRIDDOT2D file for the domain",
)
@click.option(
    "--geometry-directory",
    help="Override the geometry directory. Assumes that there is a `geo_em.d{domain_index:02}.nc`"
    " file present in the directory",
    type=click.Path(dir_okay=True, file_okay=False),
    default=lambda: os.environ.get("GEO_DIR"),
)
@click.option(
    "--output-directory",
    help="Override the output directory",
    default=None,
    type=click.Path(dir_okay=True, file_okay=False),
)
def main(
    name: str,
    version: str,
    slug: str | None,
    domain_index: int,
    cross: pathlib.Path,
    geometry_directory: str,
    output_directory: str | None,
    landuse: str,
):
    """
    Generate domain file for use by the prior

    This assumes that the WRF domain has been fetched and is present in `data/domains`
    """

    if not version.startswith("v"):
        raise click.BadParameter("Version should start with v")

    geometry_directory, output_directory = clean_directories(
        geometry_directory, output_directory, name, version
    )

    domain = create_domain_info(
        geometry_file=geometry_directory / f"geo_em.d{domain_index:02}.nc",
        cross_file=pathlib.Path(cross),
        landuse_file=pathlib.Path(landuse),
        domain_name=name,
        domain_version=version,
        domain_index=domain_index,
        domain_slug=slug if slug is not None else name,
    )

    filename = f"domain_{name}_{version}.d{domain_index:02}.nc"
    write_domain_info(domain, output_directory / filename)


if __name__ == "__main__":
    main()
