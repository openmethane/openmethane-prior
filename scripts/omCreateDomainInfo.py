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

"""
Generate domain file from example domain.

TODO: Migrate this to the `openmethane` repository as that is where the required
files are generated.
"""

import os
import pathlib
from pathlib import Path

import xarray as xr
from openmethane_prior.config import load_config_from_env

root_path = Path(__file__).parents[1]
# Root directory to use if relative paths are provided


def create_domain_info(
    geometry_file: pathlib.Path,
    cross_file: pathlib.Path,
    dot_file: pathlib.Path,
) -> xr.Dataset:
    """
    Create a new domain from the input WRF domain and subsets it to match the CMAQ domain

    Parameters
    ----------
    geometry_file
        Path to the WRF geometry file
    cross_file
        Path to the MCIP cross file
    dot_file
        Path to the MCIP dot file

    Returns
    -------
        The regridded domain information as an xarray dataset
    """
    domainXr = xr.Dataset()

    with xr.open_dataset(geometry_file) as geomXr:
        for attr in ["DX", "DY", "TRUELAT1", "TRUELAT2", "MOAD_CEN_LAT", "STAND_LON"]:
            domainXr.attrs[attr] = geomXr.attrs[attr]

    with xr.open_dataset(cross_file) as croXr:
        for var in ["LAT", "LON"]:
            domainXr[var] = croXr[var]
            domainXr[var] = croXr[var].squeeze(
                dim="LAY", drop=True
            )  # copy but remove the 'LAY' dimension

        domainXr["LANDMASK"] = croXr["LWMASK"].squeeze(
            dim="LAY", drop=True
        )  # copy but remove the 'LAY' dimension

    with xr.open_dataset(dot_file) as dotXr:
        # some repetition between the geom and grid files here, XCELL=DX and YCELL=DY
        # - XCELL, YCELL: size of a single cell in m
        # - XCENT, YCENT: lat/long of grid centre point
        # - XORIG, YORIG: position of 0,0 cell in grid coordinates (in m)
        for attr in ["XCELL", "YCELL", "XCENT", "YCENT", "XORIG", "YORIG"]:
            domainXr.attrs[attr] = croXr.attrs[attr]
        for var in ["LATD", "LOND"]:
            domainXr[var] = dotXr[var].rename({"COL": "COL_D", "ROW": "ROW_D"})

    return domainXr


if __name__ == "__main__":
    config = load_config_from_env()
    domain_path = config.input_domain_file

    domain = create_domain_info(
        geometry_file=root_path / config.geometry_file,
        cross_file=root_path / config.cro_file,
        dot_file=root_path / config.dot_file,
    )
    print(f"Writing domain to {os.path.join(root_path, domain_path)}")
    domain.to_netcdf(os.path.join(root_path, domain_path))
