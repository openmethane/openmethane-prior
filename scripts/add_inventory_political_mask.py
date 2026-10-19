#!/usr/bin/env python
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

"""
Add an `inventory_political_mask` variable to an existing domain file.

The mask marks grid cells which fall inside the Australian jurisdiction that
the national inventory reports on: land, internal waters, territorial sea and
the offshore petroleum areas. A cell is inside when any part of its area is
inside that jurisdiction.

See docs/inventory-political-mask.md for how the jurisdiction is constructed.
"""

import os
import pathlib

import click
import numpy as np
import xarray as xr

from openmethane_prior.data_sources.au_shapes import (
    amb2020_offshore_areas_data_source,
    amb2020_territorial_sea_data_source,
    au_shapes_states_data_source,
    create_inventory_political_mask,
)
from openmethane_prior.lib import logger
from openmethane_prior.lib.config import PriorConfig, fetch_domain
from openmethane_prior.lib.data_manager.manager import DataManager
from openmethane_prior.lib.grid.domain import Domain
from openmethane_prior.lib.utils import get_timestamped_command

logger = logger.get_logger(__name__)

VARIABLE_NAME = "inventory_political_mask"


def add_inventory_political_mask(
    domain_ds: xr.Dataset,
    mask: np.ndarray,
    grid_mapping: str,
) -> xr.Dataset:
    """Return a copy of the domain with the mask added as inventory_political_mask."""
    domain_ds = domain_ds.copy()
    domain_ds[VARIABLE_NAME] = xr.DataArray(
        dims=("y", "x"),
        data=mask,
        attrs={
            "units": "1",
            "long_name": (
                "mask of the political boundary covered by the inventory (1=inside, 0=outside)"
            ),
            "flag_values": np.array([0, 1], dtype=np.int8),
            "flag_meanings": "outside inside",
            "grid_mapping": grid_mapping,
            "comment": (
                "Cells with any area inside Australian land, internal waters, territorial sea "
                "or offshore petroleum areas. Not used by the prior to allocate emissions. "
                "See docs/inventory-political-mask.md in openmethane-prior."
            ),
            "source": (
                "Geoscience Australia Australian Maritime Boundaries 2020 (AMB2020), CC BY 4.0; "
                "ABS ASGS Edition 3 State and Territory boundaries 2021, CC BY 4.0"
            ),
        },
    )
    history = domain_ds.attrs.get("history", "")
    domain_ds.attrs["history"] = f"{get_timestamped_command()}\n{history}".strip()
    return domain_ds


@click.command(name="add_inventory_political_mask")
@click.option(
    "--domain",
    "domain_file",
    type=str,
    required=False,
    help="Path or URL of the domain to add the mask to. Overrides DOMAIN_FILE",
)
@click.option(
    "--output",
    "output_file",
    type=click.Path(dir_okay=False, path_type=pathlib.Path),
    required=True,
    help="Path to write the updated domain file to. Must differ from --domain",
)
def main(domain_file: str | None, output_file: pathlib.Path):
    """Add an inventory_political_mask variable to an existing domain file.

    Paths and the domain are read from the environment or .env like
    omPrior.py, with --domain taking precedence over DOMAIN_FILE.
    """
    # set CLI options as environment variables before PriorConfig reads .env,
    # which does not override variables that are already set
    if domain_file is not None:
        os.environ["DOMAIN_FILE"] = domain_file
    # PriorConfig requires a start date, but the data sources used to build
    # the mask are not time-dependent
    os.environ.setdefault("START_DATE", "2000-01-01")
    config = PriorConfig.from_env()
    config.prepare_paths()
    data_manager = DataManager.from_config(config)

    # read the domain the same way the prior does, which may fetch it
    domain_path = fetch_domain(config.domain_path, config.input_path)
    if output_file.resolve() == domain_path.resolve():
        raise click.BadParameter("--output must differ from the domain file")
    logger.info(f"Adding {VARIABLE_NAME} to {domain_path}")
    domain = Domain.from_file(domain_path)
    logger.info("Masking grid cells inside Australian jurisdiction (AMB2020 and ABS states)")
    mask = create_inventory_political_mask(
        grid=domain.grid,
        states=data_manager.get_asset(au_shapes_states_data_source).data,
        territorial_sea=data_manager.get_asset(amb2020_territorial_sea_data_source).data,
        offshore_areas=data_manager.get_asset(amb2020_offshore_areas_data_source).data,
    )
    logger.info(f"{int(mask.sum())} of {mask.size} cells inside the jurisdiction")

    with domain.dataset as source_ds:
        domain_ds = add_inventory_political_mask(
            domain_ds=source_ds.load(),
            mask=mask,
            grid_mapping=source_ds["land_mask"].attrs["grid_mapping"],
        )

    logger.info(f"Writing domain to {output_file}")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    # xarray doesn't carry over compression for variable-length strings, so
    # cell_name would be written uncompressed and add about 3 MB to aust10km
    encoding = {}
    if "cell_name" in domain_ds:
        encoding["cell_name"] = {"zlib": True, "complevel": 4, "shuffle": True}
    domain_ds.to_netcdf(output_file, encoding=encoding)


if __name__ == "__main__":
    main()
