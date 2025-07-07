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


@attrs.frozen()
class PublishedInputDomain:
    """
    Input domain configuration

    Used to specify the published domain to use as the input domain.
    """

    name: str
    version: str
    domain_index: int = 1

    def url_fragment(self) -> str:
        """
        Fragment to download the input domain

        Returns
        -------
            URL fragment
        """
        return (
            f"domains/{self.name}/{self.version}/"
            f"prior_domain_{self.name}_{self.version}.d{self.domain_index:02}.nc"
        )

class PriorConfigOptions(typing.TypedDict, total=False):
    remote: str
    input_path: pathlib.Path | str
    output_path: pathlib.Path | str
    intermediates_path: pathlib.Path | str
    input_domain: PublishedInputDomain | str
    output_filename: str
    layer_inputs: LayerInputs

@attrs.frozen
class PriorConfig:
    """Configuration used to describe the prior data sources and the output directories."""

    remote: str
    input_path: pathlib.Path
    output_path: pathlib.Path
    intermediates_path: pathlib.Path

    input_domain: PublishedInputDomain | str
    """Input domain specification

    If provided, use a published domain as the input domain. Otherwise, a file
    specified in the `DOMAIN` env variable is used as the input domain.
    """

    output_filename: str
    """Filename to write the prior output to as a NetCDFv4 file in
    `output_path`"""

    layer_inputs: LayerInputs

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
        if isinstance(self.input_domain, PublishedInputDomain):
            return self.as_input_file(self.input_domain.url_fragment())
        elif isinstance(self.input_domain, str):
            return self.as_input_file(self.input_domain)
        else:
            raise TypeError("Could not interpret the 'input_domain' field")

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

    if env.str("DOMAIN_NAME", None) and env.str("DOMAIN_VERSION", None):
        input_domain = PublishedInputDomain(
            name=env.str("DOMAIN_NAME"),
            version=env.str("DOMAIN_VERSION"),
        )
    else:
        # Default to using a user-specified file as the input domain
        input_domain = env.str("DOMAIN")

    options: PriorConfigOptions = dict(
        remote=env.str("PRIOR_REMOTE"),
        input_path=env.path("INPUTS", "data/inputs"),
        output_path=env.path("OUTPUTS", "data/outputs"),
        intermediates_path=env.path("INTERMEDIATES", "data/processed"),
        input_domain=input_domain,
        output_filename=env.str("OUTPUT_FILENAME", "prior_emissions.nc"),
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
    )

    return PriorConfig(**{**options, **overrides})
