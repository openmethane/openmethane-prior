import argparse
from attrs import field, frozen
from attrs.converters import default_if_none
import datetime
from environs import Env
import os
import pathlib
import shutil
from typing import Self

from .data_manager.source import DataSource
from .grid.domain import Domain, parse_domain


@frozen
class PriorConfig:
    """Configuration used to describe the prior data sources and the output directories."""

    domain_path: pathlib.Path | str
    """URL or file path to the domain of interest. Relative paths
    will be interpreted relative to input_path"""

    start_date: datetime.datetime
    """Start of the period over which emissions should be estimated."""
    end_date: datetime.datetime | None = None
    """End of the period over which emissions should be estimated. If not
    provided, estimates will cover a single day specified by start_date."""

    sectors: tuple[str] | None = None
    """List of PriorSector names to process"""

    # workaround for from_env having to specify None values for missing paths
    # is to set the value using default_if_none
    input_path: pathlib.Path = field(
        default=None, converter=default_if_none(pathlib.Path("data/inputs")),
    )
    """Filesystem path where input files exist or should be fetched to."""
    output_path: pathlib.Path = field(
        default=None, converter=default_if_none(pathlib.Path("data/outputs")),
    )
    """Filesystem path where outputs should be created."""
    intermediates_path: pathlib.Path = field(
        default=None, converter=default_if_none(pathlib.Path("data/intermediates")),
    )
    """Filesystem path where intermediate artifacts should be stored."""

    output_filename: str = field(
        default=None, converter=default_if_none("prior-emissions.nc"),
    )
    """Filename to write the prior output to as a NetCDFv4 file in
    `output_path`"""

    input_cache: pathlib.Path = None
    """If provided, a local path where remote inputs can be cached."""

    domain: Domain | None = None
    """The parsed domain. Populated after the domain DataSource has been
    fetched and parsed by the DataManager. Must be resolved before any
    DataSource whose parser depends on the domain CRS is fetched."""

    # __attrs_post_init__ is called automatically after the __init__ generated
    # by attrs has run.
    # @see: https://www.attrs.org/en/stable/init.html
    def __attrs_post_init__(self):
        # if no end_date is provided, estimate a single day specified by start_date
        if self.end_date is None:
            # can't set attributes on frozen class
            object.__setattr__(self, "end_date", self.start_date)


    def as_input_file(self, name: str | pathlib.Path) -> pathlib.Path:
        """Return the full path to an input file"""
        return self.input_path / name

    def as_intermediate_file(self, name: str | pathlib.Path) -> pathlib.Path:
        """Return the full path to an intermediate file"""
        return self.intermediates_path / name

    def as_output_file(self, name: str | pathlib.Path) -> pathlib.Path:
        """Return the full path to an output file"""
        return self.output_path / name

    def prepare_paths(self):
        """Create any configured directory paths that don't already exist."""
        self.input_path.mkdir(parents=True, exist_ok=True)
        self.intermediates_path.mkdir(parents=True, exist_ok=True)
        self.output_path.mkdir(parents=True, exist_ok=True)

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

    @property
    def domain_source(self) -> DataSource:
        """DataSource based on the path or URL supplied in the domain_path."""
        return DataSource(
            name="domain",
            # basic_fetch supports file path or url
            url=str(self.domain_path),
            parse=lambda data_source: parse_domain(data_source.asset_path),
        )

    @property
    def output_file(self):
        """Get the filename of the output domain"""
        return self.as_output_file(self.output_filename)

    @classmethod
    def from_env(cls) -> Self:
        """Load config from environment variables, or an `.env` file."""
        env = Env(expand_vars=True)
        env.read_env(verbose=True)

        # read START_DATE and convert to a datetime at midnight
        start_date = env.date("START_DATE")
        start_date = datetime.datetime.combine(start_date, datetime.time.min)

        end_date = env.date("END_DATE", None)
        if end_date:
            end_date = datetime.datetime.combine(end_date, datetime.time.min)

        # split a string like "agriculture,coal,waste" into a list
        sectors = env.str("SECTORS", "").split(",")
        sectors = tuple([s for s in sectors if s != ""]) # filter out empty strings

        return cls(
            # required
            domain_path=env.str("DOMAIN_FILE"),
            start_date=start_date,
            end_date =end_date,
            # use defaults
            input_path=env.path("INPUTS", None),
            output_path=env.path("OUTPUTS", None),
            intermediates_path=env.path("INTERMEDIATES", None),
            input_cache=env.path("INPUT_CACHE", None),
            output_filename=env.str("OUTPUT_FILENAME", None),
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

    if args.sectors is not None:
        os.environ["SECTORS"] = args.sectors