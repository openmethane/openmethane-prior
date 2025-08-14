#!/usr/bin/env python
#
# Copyright 2025 The Superpower Institute Ltd.
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
Generate domain file for use by Open Methane prior and alerts, by subsetting
an existing domain.

See create_prior_domain.py for creating a new domain from scratch.
"""

import os
import pathlib
import click
import xarray as xr

from openmethane_prior.utils import get_timestamped_command, get_version, list_cf_grid_mappings
import openmethane_prior.logger as logger

logger = logger.get_logger(__name__)

def create_subset_domain(
    from_domain: pathlib.Path,
    origin: tuple[int, int],
    dimensions: tuple[int, int],
    domain_name: str,
    domain_version: str,
    domain_index: int,
    domain_slug: str,
) -> xr.Dataset:
    """
    Create a new domain subset from an existing prior domain.

    :param from_domain: The original domain to take a subset from.
    :param origin: The x, y cell index coordinates of the grid cell which is
      the lower left corner cell of the subset domain.
    :param dimensions: The x, y dimensions, in number of cells, that define the
      size of the subset domain. 10,10 would make a 10x10 cell domain.
    :param domain_name: The name of the new domain
    :param domain_version: The version of the domain being generated
    :param domain_index: The subdomain index
    :param domain_slug: A short, URL-safe name for the domain
    :return: The re-gridded domain information as an xarray Dataset
    """

    """

    """
    parent_domain_ds = xr.open_dataset(from_domain)

    logger.info(f"Subsetting domain {parent_domain_ds.domain_name} from origin {origin}")
    subset_domain_ds = parent_domain_ds.isel(
        x=slice(origin[0], origin[0] + dimensions[0]),
        y=slice(origin[1], origin[1] + dimensions[1]),
    )

    projection_var_name = list_cf_grid_mappings(subset_domain_ds)[0]

    domain_ds = xr.Dataset(
        coords={
            "x": subset_domain_ds.coords["x"],
            "y": subset_domain_ds.coords["y"],
        },
        data_vars={
            # meta data
            "lat": subset_domain_ds["lat"],
            "lon": subset_domain_ds["lon"],
            "x_bounds": subset_domain_ds["x_bounds"],
            "y_bounds": subset_domain_ds["y_bounds"],
            projection_var_name: subset_domain_ds[projection_var_name],

            "cell_name": subset_domain_ds["cell_name"],

            # data variables
            "land_mask": subset_domain_ds["land_mask"],
            "LANDMASK": subset_domain_ds["LANDMASK"],
        },
        attrs={
            # data attributes
            "DX": subset_domain_ds.DX,
            "DY": subset_domain_ds.DY,
            "XCELL": subset_domain_ds.XCELL,
            "YCELL": subset_domain_ds.YCELL,

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

    # compress cell_names which take a lot of space
    domain_ds.cell_name.encoding["zlib"] = True

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
    "--from-domain",
    type=click.Path(exists=True, file_okay=True),
    required=True,
    help="Path to the parent domain which the new domain will be subset from",
)
@click.option(
    "--origin",
    type=str,
    required=True,
    help="Cell index coordinates of the lower left corner of the new domain, in the form: x,y",
)
@click.option(
    "--dimensions",
    type=str,
    required=True,
    help="Number of cells in the new domain, in the form: width,height",
)
@click.option(
    "--output-directory",
    help="Override the output directory. Defaults to geometry directory if not set.",
    default=None,
    type=click.Path(dir_okay=True, file_okay=False),
)
def main(
    name: str,
    version: str,
    slug: str | None,
    domain_index: int,
    from_domain: pathlib.Path,
    origin: str,
    dimensions: str,
    output_directory: pathlib.Path | None,
):
    """
    Generate domain file for use by the prior

    This assumes that the WRF domain has been fetched and is present in `data/domains`
    """

    if not version.startswith("v"):
        raise click.BadParameter("Version should start with v")

    origin_x, origin_y = origin.split(",")
    dimensions_x, dimensions_y = dimensions.split(",")

    domain = create_subset_domain(
        domain_name=name,
        domain_version=version,
        domain_index=domain_index,
        domain_slug=slug if slug is not None else name,
        from_domain=from_domain,
        origin=(int(origin_x), int(origin_y)),
        dimensions=(int(dimensions_x), int(dimensions_y)),
    )

    filename = f"domain.{name}.nc"
    write_domain_info(domain, pathlib.Path(output_directory or pathlib.Path.cwd()) / filename)


if __name__ == "__main__":
    main()
