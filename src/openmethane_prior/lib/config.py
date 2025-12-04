import argparse
import datetime
import os
import pathlib
import shutil
from typing import Self, TypedDict
from functools import cache

import attrs
import pyproj
import xarray as xr
from environs import Env

from .grid.grid import Grid
from .grid.create_grid import create_grid_from_domain, create_grid_from_mcip
from .utils import is_url


class PriorConfigOptions(TypedDict, total=False):
    input_path: pathlib.Path | str
    output_path: pathlib.Path | str
    intermediates_path: pathlib.Path | str
    input_cache: pathlib.Path | str | None
    domain_path: pathlib.Path | str
    inventory_domain_path: pathlib.Path | str
    output_filename: str
    start_date: datetime.datetime
    end_date: datetime.datetime
    sectors: tuple[str] | None

@attrs.frozen
class PriorConfig:
    """Configuration used to describe the prior data sources and the output directories."""

    input_path: pathlib.Path
    output_path: pathlib.Path
    intermediates_path: pathlib.Path

    domain_path: pathlib.Path | str
    """URL or file path to the domain of interest. Relative paths
    will be interpreted relative to input_path"""
    inventory_domain_path: pathlib.Path | str
    """URL or file path to the inventory domain of interest. Relative paths
    will be interpreted relative to input_path"""

    output_filename: str = "prior-emissions.nc"
    """Filename to write the prior output to as a NetCDFv4 file in
    `output_path`"""

    sectors: tuple[str] | None = None
    """List of PriorSector names to process"""

    start_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None

    input_cache: pathlib.Path = None
    """If provided, a local path where remote inputs can be cached."""

    def __attrs_post_init__(self):
        """When created, ensure all configured paths exist, and populate inputs
        from the input_cache, if configured."""
        self.input_path.mkdir(parents=True, exist_ok=True)
        self.intermediates_path.mkdir(parents=True, exist_ok=True)
        self.output_path.mkdir(parents=True, exist_ok=True)


    def as_input_file(self, name: str | pathlib.Path) -> pathlib.Path:
        """Return the full path to an input file"""
        return self.input_path / name

    def as_intermediate_file(self, name: str | pathlib.Path) -> pathlib.Path:
        """Return the full path to an intermediate file"""
        return self.intermediates_path / name

    def as_output_file(self, name: str | pathlib.Path) -> pathlib.Path:
        """Return the full path to an output file"""
        return self.output_path / name

    def load_cached_inputs(self):
        """Copy the contents of the input cache into the input folder."""
        if self.input_cache is not None and self.input_cache.exists():
            shutil.copytree(src=self.input_cache, dst=self.input_path, dirs_exist_ok=True)

    def cache_inputs(self):
        """Copy everything in the inputs folder back into the cache, so that
        any new inputs fetched during this run will be cached."""
        if self.input_cache is not None:
            self.input_cache.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src=self.input_path, dst=self.input_cache, dirs_exist_ok=True)

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
        """Filesystem path of the input domain"""
        if is_url(self.domain_path):
            return self.as_input_file(os.path.basename(self.domain_path))
        elif not self.domain_path.startswith("/"):
            return self.as_input_file(self.domain_path)
        return pathlib.Path(self.domain_path)

    @property
    def inventory_domain_file(self):
        """Filesystem path of the inventory domain"""
        if is_url(self.inventory_domain_path):
            return self.as_input_file(os.path.basename(self.inventory_domain_path))
        elif not self.inventory_domain_path.startswith("/"):
            return self.as_input_file(self.inventory_domain_path)
        return pathlib.Path(self.inventory_domain_path)

    @property
    def output_file(self):
        """Get the filename of the output domain"""
        return self.as_output_file(self.output_filename)

    @classmethod
    def from_env(cls) -> Self:
        """Load config from environment variables, or an `.env` file."""
        env = Env(expand_vars=True)
        env.read_env(verbose=True)

        start_date = env.date("START_DATE", None)
        # if END_DATE not set, use START_DATE for a 1-day run
        end_date = env.date("END_DATE", None) or env.date("START_DATE", None)
        # now convert both to datetime.datetime
        if start_date:
            start_date = datetime.datetime.combine(start_date, datetime.time.min)
        if end_date:
            end_date = datetime.datetime.combine(end_date, datetime.time.min)

        sectors = env.str("SECTORS", "").split(",")
        sectors = tuple([s for s in sectors if s != ""]) # filter out empty strings

        return cls(
            input_path=env.path("INPUTS", "data/inputs"),
            output_path=env.path("OUTPUTS", "data/outputs"),
            intermediates_path=env.path("INTERMEDIATES", "data/processed"),
            input_cache=env.path("INPUT_CACHE", None),
            domain_path=env.str("DOMAIN_FILE"),
            inventory_domain_path=env.str("INVENTORY_DOMAIN_FILE"),
            output_filename=env.str("OUTPUT_FILENAME", "prior-emissions.nc"),
            start_date=start_date,
            end_date =end_date,
            sectors=sectors if len(sectors) > 0 else None,
        )

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
        "--sectors",
        default=None,
        help="list of sectors to process, comma-separated",
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

    if args.sectors is not None:
        os.environ["SECTORS"] = args.sectors