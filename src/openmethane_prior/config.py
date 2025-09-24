import argparse
import datetime
import os
import pathlib
import typing
from functools import cache

import attrs
import pyproj
import xarray as xr
from environs import Env

from .grid.grid import Grid
from .grid.create_grid import create_grid_from_domain, create_grid_from_mcip
from .utils import is_url


@attrs.frozen()
class LayerInputs:
    """
    Filename fragments for the files required to generate the layers.

    These files are downloaded to the `INPUTS` directory via `scripts/omDownloadInputs.py`.
    """
    aus_shapefile_path: pathlib.Path
    termite_path: pathlib.Path
    wetland_path: pathlib.Path


class PriorConfigOptions(typing.TypedDict, total=False):
    remote: str
    input_path: pathlib.Path | str
    output_path: pathlib.Path | str
    intermediates_path: pathlib.Path | str
    domain_path: pathlib.Path | str
    inventory_domain_path: pathlib.Path | str
    output_filename: str
    layer_inputs: LayerInputs
    start_date: datetime.datetime
    end_date: datetime.datetime

@attrs.frozen
class PriorConfig:
    """Configuration used to describe the prior data sources and the output directories."""

    remote: str
    input_path: pathlib.Path
    output_path: pathlib.Path
    intermediates_path: pathlib.Path

    domain_path: pathlib.Path | str
    """URL or file path to the domain of interest. Relative paths
    will be interpreted relative to input_path"""
    inventory_domain_path: pathlib.Path | str
    """URL or file path to the inventory domain of interest. Relative paths
    will be interpreted relative to input_path"""

    output_filename: str
    """Filename to write the prior output to as a NetCDFv4 file in
    `output_path`"""

    layer_inputs: LayerInputs

    start_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None

    def as_input_file(self, name: str | pathlib.Path) -> pathlib.Path:
        """Return the full path to an input file"""
        return self.input_path / name

    def as_intermediate_file(self, name: str | pathlib.Path) -> pathlib.Path:
        """Return the full path to an intermediate file"""
        return self.intermediates_path / name

    def as_output_file(self, name: str | pathlib.Path) -> pathlib.Path:
        """Return the full path to an output file"""
        return self.output_path / name

    @cache
    def domain_dataset(self):
        """Load the input domain dataset"""
        if not self.domain_file.exists():
            raise ValueError(f"Missing domain file: {self.domain_file}")
        return xr.open_dataset(self.domain_file)

    @cache
    def inventory_dataset(self):
        """Load the inventory domain dataset"""
        if not self.inventory_domain_file.exists():
            raise ValueError(f"Missing inventory domain file: {self.inventory_domain_file}")
        return xr.open_dataset(self.inventory_domain_file)


    @cache
    def domain_grid(self) -> Grid:
        """Create a Grid from the domain dataset"""
        domain_ds = self.domain_dataset()
        if ("Conventions" in domain_ds.attrs):
            return create_grid_from_domain(domain_ds)
        return create_grid_from_mcip(
            TRUELAT1=domain_ds.TRUELAT1,
            TRUELAT2=domain_ds.TRUELAT2,
            MOAD_CEN_LAT=domain_ds.MOAD_CEN_LAT,
            STAND_LON=domain_ds.STAND_LON,
            COLS=domain_ds.COL.size,
            ROWS=domain_ds.ROW.size,
            XCENT=domain_ds.XCENT,
            YCENT=domain_ds.YCENT,
            XORIG=domain_ds.XORIG,
            YORIG=domain_ds.YORIG,
            XCELL=domain_ds.XCELL,
            YCELL=domain_ds.YCELL,
        )

    @cache
    def domain_projection(self) -> pyproj.Proj:
        """Query the projection used by the input domain"""
        return self.domain_grid().projection

    @cache
    def inventory_grid(self) -> Grid:
        """Create a Grid from the inventory dataset"""
        return create_grid_from_domain(domain_ds=self.inventory_dataset())

    @cache
    def inventory_projection(self) -> pyproj.Proj:
        """Query the projection used by the inventory domain"""
        return self.inventory_grid().projection

    @property
    def crs(self):
        """Return the CRS used by the domain dataset"""
        return self.domain_projection().crs

    @property
    def domain_file(self):
        """
        Get the filename of the input domain

        If specified as a URL, this assumes the file has been downloaded by
        omDownloadInputs.py
        """
        if is_url(self.domain_path):
            return self.as_input_file(os.path.basename(self.domain_path))
        elif not self.domain_path.startswith("/"):
            return self.as_input_file(self.domain_path)
        return pathlib.Path(self.domain_path)

    @property
    def inventory_domain_file(self):
        """
        Get the filename of the inventory domain
        """
        if is_url(self.inventory_domain_path):
            return self.as_input_file(os.path.basename(self.inventory_domain_path))
        elif not self.inventory_domain_path.startswith("/"):
            return self.as_input_file(self.inventory_domain_path)
        return pathlib.Path(self.inventory_domain_path)

    @property
    def output_file(self):
        """Get the filename of the output domain"""
        return self.as_output_file(self.output_filename)


def load_config_from_env(**overrides: PriorConfigOptions) -> PriorConfig:
    """
    Load the configuration from the environment variables

    This also loads environment variables from a local `.env` file.

    Returns
    -------
        Application configuration
    """
    env = Env(
        expand_vars=True,
    )
    env.read_env(verbose=True)

    start_date = env.date("START_DATE", None)
    # if END_DATE not set, use START_DATE for a 1-day run
    end_date = env.date("END_DATE", None) or env.date("START_DATE", None)
    # now convert both to datetime.datetime
    if start_date:
        start_date = datetime.datetime.combine(start_date, datetime.time.min)
    if end_date:
        end_date = datetime.datetime.combine(end_date, datetime.time.min)

    options: PriorConfigOptions = dict(
        remote=env.str("PRIOR_REMOTE"),
        input_path=env.path("INPUTS", "data/inputs"),
        output_path=env.path("OUTPUTS", "data/outputs"),
        intermediates_path=env.path("INTERMEDIATES", "data/processed"),
        domain_path=env.str("DOMAIN_FILE"),
        inventory_domain_path=env.str("INVENTORY_DOMAIN_FILE"),
        output_filename=env.str("OUTPUT_FILENAME", "prior-emissions.nc"),
        layer_inputs=LayerInputs(
            aus_shapefile_path=env.path("AUSF"),
            termite_path=env.path("TERMITES"),
            wetland_path=env.path("WETLANDS"),
        ),
        start_date=start_date,
        end_date =end_date,
    )

    return PriorConfig(**{**options, **overrides})

def parse_cli_args():
    """
    Set up common CLI arguments that can be read in at start time.
    """
    parser = argparse.ArgumentParser(
        description="Calculate the prior methane emissions estimate for Open Methane"
    )
    parser.add_argument(
        "--start-date",
        type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"),
        help="Start date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--end-date",
        type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"),
        help="end date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--skip-reproject",
        default=False,
        action="store_true", # set as True if present
    )

    return parser.parse_args()

def parse_cli_to_env():
    """
    Parse CLI arguments and set them as environment variables so they can be
    read in by the config.
    """
    args = parse_cli_args()

    if args.start_date is not None:
        os.environ["START_DATE"] = args.start_date.strftime("%Y-%m-%d")

    if args.end_date is not None:
        os.environ["END_DATE"] = args.end_date.strftime("%Y-%m-%d")
    elif args.start_date is not None:
        os.environ["END_DATE"] = args.start_date.strftime("%Y-%m-%d")
