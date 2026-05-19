import argparse
from attrs import field, frozen
from attrs.converters import default_if_none
import datetime
from environs import Env
import os
import pathlib
import shutil
from typing import Self
import urllib.request

from .grid.domain import Domain


@frozen
class PriorConfig:
    """Static configuration describing where the prior reads inputs and writes
    outputs. Set once per environment and does not change between runs."""

    domain_path: str
    """URL or file path to the domain of interest."""

    start_date: datetime.datetime
    """Start of the period over which emissions should be estimated."""

    end_date: datetime.datetime | None = None
    """End of the period over which emissions should be estimated. If not
    provided, estimates will cover a single day specified by start_date."""

    sectors: tuple[str] | None = None
    """Names of the PriorSector modules to process. None means all sectors."""

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

    # __attrs_post_init__ is called automatically after the __init__ generated
    # by attrs has run.
    # @see: https://www.attrs.org/en/stable/init.html
    def __attrs_post_init__(self):
        # if no end_date is provided, estimate a single day specified by start_date
        if self.end_date is None:
            # can't set attributes on frozen class
            object.__setattr__(self, "end_date", self.start_date)

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
    def output_file(self):
        """Get the filename of the output file"""
        return self.output_path / self.output_filename

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
        sectors = tuple([s for s in sectors if s != ""])

        return cls(
            domain_path=env.str("DOMAIN_FILE"),
            start_date=start_date,
            end_date=end_date,
            sectors=sectors if len(sectors) > 0 else None,
            input_path=env.path("INPUTS", None),
            output_path=env.path("OUTPUTS", None),
            intermediates_path=env.path("INTERMEDIATES", None),
            input_cache=env.path("INPUT_CACHE", None),
            output_filename=env.str("OUTPUT_FILENAME", None),
        )


@frozen
class PriorParameters:
    """Per-run parameters that control a single execution of the prior.
    May change between runs (e.g. different date range or domain)."""

    domain: Domain
    """The domain of interest, parsed as a Domain."""

    start_date: datetime.datetime
    """Start of the period over which emissions should be estimated."""

    end_date: datetime.datetime
    """End of the period over which emissions should be estimated."""


    @property
    def crs(self):
        """Return the CRS used by the domain."""
        return self.domain.crs

    @classmethod
    def from_config(cls, config: PriorConfig) -> Self:
        """Extract the runtime parameters from the config which are needed
        to control the period and domain of emission estimates."""
        domain_file = fetch_domain(config.domain_path, config.input_path)
        domain = Domain.from_file(domain_file)

        return cls(
            domain=domain,
            start_date=config.start_date,
            end_date=config.end_date,
        )


def fetch_domain(
    path_or_url: pathlib.Path | str,
    input_path: pathlib.Path,
) -> pathlib.Path:
    domain_file = input_path / os.path.basename(str(path_or_url))
    if not os.path.exists(domain_file):
        urllib.request.urlretrieve(url=str(path_or_url), filename=domain_file)
    return domain_file


def parse_cli_args():
    """Set up common CLI arguments that can be read in at start time."""
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
    """Parse CLI arguments and set them as environment variables so they can be
    read in by the config"""
    args = parse_cli_args()

    if args.start_date is not None:
        os.environ["START_DATE"] = args.start_date.strftime("%Y-%m-%d")

    if args.end_date is not None:
        os.environ["END_DATE"] = args.end_date.strftime("%Y-%m-%d")

    if args.sectors is not None:
        os.environ["SECTORS"] = args.sectors
