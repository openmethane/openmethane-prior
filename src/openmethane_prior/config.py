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

from .grid.domain_grid import DomainGrid

@attrs.frozen()
class LayerInputs:
    """
    Filename fragments for the files required to generate the layers.

    These files are downloaded to the `INPUTS` directory via `scripts/omDownloadInputs.py`.
    """

    electricity_path: pathlib.Path
    oil_gas_path: pathlib.Path
    coal_path: pathlib.Path
    land_use_path: pathlib.Path
    sectoral_emissions_path: pathlib.Path
    sectoral_mapping_path: pathlib.Path
    ntl_path: pathlib.Path
    aus_shapefile_path: pathlib.Path
    livestock_path: pathlib.Path
    termite_path: pathlib.Path
    wetland_path: pathlib.Path


class InputDomain:
    path: pathlib.Path
    name: str
    version: str
    domain_index: int
    slug: str

    def __init__(self,
            path: str | pathlib.Path,
            name: str | None = None,
            version: str | None = None,
            domain_index: int | None = None,
            slug: str | None = None,
        ):
        self.path = pathlib.Path(path)
        self.name = name or self.path.stem
        self.version = version or "v1"
        self.domain_index = domain_index or 1
        self.slug = slug or self.name

        # TODO this should be embedded in the domain file as an attribute
        # TODO remove matching test assertion when this is removed
        if (self.slug == "aust10km"): self.slug = "10"

class PublishedInputDomain(InputDomain):
    """
    Input domain configuration

    Used to specify the published domain to use as the input domain.
    """
    def __init__(self,
        name: str,
        version: str | None = "v1",
        domain_index: int | None = 1,
        slug: str | None = None,
    ):
        published_path = pathlib.Path(
            f"domains/{name}/{version}/"
            f"prior_domain_{name}_{version}.d{domain_index:02}.nc"
        )

        super().__init__(
            path=published_path,
            name=name,
            version=version,
            domain_index=domain_index,
            slug=slug,
        )

class PriorConfigOptions(typing.TypedDict, total=False):
    remote: str
    input_path: pathlib.Path | str
    output_path: pathlib.Path | str
    intermediates_path: pathlib.Path | str
    input_domain: InputDomain
    output_filename: str
    layer_inputs: LayerInputs
    start_date: datetime.datetime
    end_date: datetime.datetime
    skip_reproject: bool

@attrs.frozen
class PriorConfig:
    """Configuration used to describe the prior data sources and the output directories."""

    remote: str
    input_path: pathlib.Path
    output_path: pathlib.Path
    intermediates_path: pathlib.Path

    input_domain: InputDomain
    """Input domain specification

    If provided, use a published domain as the input domain. Otherwise, a file
    specified in the `DOMAIN` env variable is used as the input domain.
    """

    output_filename: str
    """Filename to write the prior output to as a NetCDFv4 file in
    `output_path`"""

    layer_inputs: LayerInputs

    start_date: datetime.datetime | None = None
    end_date: datetime.datetime | None = None

    skip_reproject: bool = False

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
        if not self.input_domain_file.exists():
            raise ValueError(f"Missing domain file: {self.input_domain_file}")
        return xr.open_dataset(self.input_domain_file)

    @cache
    def domain_grid(self) -> DomainGrid:
        """Create a Grid from the domain dataset"""
        return DomainGrid(domain_ds=self.domain_dataset())

    @cache
    def domain_projection(self) -> pyproj.Proj:
        """Query the projection used by the input domain"""
        return self.domain_grid().projection

    @property
    def crs(self):
        """Return the CRS used by the domain dataset"""
        return self.domain_projection().crs

    @property
    def input_domain_file(self):
        """
        Get the filename of the input domain

        Uses a published domain if it is provided otherwise uses a user-specified file name
        """
        return self.as_input_file(self.input_domain.path)

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

    if env.str("DOMAIN", None):
        input_domain = InputDomain(
            path=env.str("DOMAIN"),
            name=env.str("DOMAIN_NAME", None),
            version=env.str("DOMAIN_VERSION", None),
        )
    elif env.str("DOMAIN_NAME", None) and env.str("DOMAIN_VERSION", None):
        input_domain = PublishedInputDomain(
            name=env.str("DOMAIN_NAME"),
            version=env.str("DOMAIN_VERSION"),
        )
    else:
        raise ValueError("Must specify DOMAIN, or DOMAIN_NAME and DOMAIN_VERSION")

    options: PriorConfigOptions = dict(
        remote=env.str("PRIOR_REMOTE"),
        input_path=env.path("INPUTS", "data/inputs"),
        output_path=env.path("OUTPUTS", "data/outputs"),
        intermediates_path=env.path("INTERMEDIATES", "data/processed"),
        input_domain=input_domain,
        output_filename=env.str("OUTPUT_FILENAME", "prior-emissions.nc"),
        layer_inputs=LayerInputs(
            electricity_path=env.path("CH4_ELECTRICITY"),
            oil_gas_path=env.path("CH4_OILGAS"),
            coal_path=env.path("CH4_COAL"),
            land_use_path=env.path("LAND_USE"),
            sectoral_emissions_path=env.path("SECTORAL_EMISSIONS"),
            sectoral_mapping_path=env.path("SECTORAL_MAPPING"),
            ntl_path=env.path("NTL"),
            aus_shapefile_path=env.path("AUSF"),
            livestock_path=env.path("LIVESTOCK_DATA"),
            termite_path=env.path("TERMITES"),
            wetland_path=env.path("WETLANDS"),
        ),
        start_date=env.datetime("START_DATE", None),
        # if END_DATE not set, use START_DATE for a 1-day run
        end_date=env.datetime("END_DATE", None) or env.datetime("START_DATE", None),
        skip_reproject=env.bool("SKIP_REPROJECT", False),
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

    os.environ["SKIP_REPROJECT"] = "True" if args.skip_reproject else "False"
