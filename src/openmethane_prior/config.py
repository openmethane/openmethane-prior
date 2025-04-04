import pathlib
import typing
from functools import cache

import attrs
import pyproj
import xarray as xr
from environs import Env


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


@attrs.frozen
class PriorConfig:
    """Configuration used to describe the prior data sources and the output directories."""

    remote: str
    input_path: pathlib.Path
    output_path: pathlib.Path
    intermediates_path: pathlib.Path

    input_domain: PublishedInputDomain | str
    """Input domain specification

    If provided, use a published domain as the input domain.
    Otherwise, a file named `output_domain` is used as the input domain.
    """
    output_domain: str
    """Name of the output domain file"""
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

    def llc_xy(self) -> tuple[float, float]:
        """Get the x, y coordinates of the lower left corner of the domain"""
        llc_lat = self.domain_dataset()["LATD"].to_numpy().flatten()[0]
        llc_lon = self.domain_dataset()["LOND"].to_numpy().flatten()[0]
        llc_x, llc_y = self.domain_projection()(llc_lon, llc_lat)
        return llc_x, llc_y

    @cache
    def domain_dataset(self):
        """Load the input domain dataset"""
        if not self.input_domain_file.exists():
            raise ValueError(f"Missing domain file: {self.input_domain_file}")
        return xr.load_dataset(self.input_domain_file)
    @cache
    def inventory_domain_dataset(self):
        """Load the inventory domain dataset"""
        if not self.inventory_domain_file.exists():
            raise ValueError(f"Missing domain file: {self.inventory_domain_file}")
        return xr.load_dataset(self.inventory_domain_file)

    @cache
    def domain_projection(self):
        """Query the projection used by the input domain"""
        ds = self.domain_dataset()

        return pyproj.Proj(
            proj="lcc",
            lat_1=ds.TRUELAT1,
            lat_2=ds.TRUELAT2,
            lat_0=ds.MOAD_CEN_LAT,
            lon_0=ds.STAND_LON,
            # https://github.com/openmethane/openmethane-prior/issues/24
            # x_0=domainXr.XORIG,
            # y_0=domainXr.YORIG,
            a=6370000,
            b=6370000,
        )

    @property
    def crs(self):
        """Return the CRS used by the domain dataset"""
        return self.domain_projection().crs

    @property
    def domain_cell_area(self):
        """Calculate the cell area for each cell"""
        ds = self.domain_dataset()
        return ds.DX * ds.DY

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
    def inventory_domain_file(self):
        """
        Get the filename of the inventory domain

        Uses a published domain if it is provided otherwise uses a user-specified file name
        """
        if isinstance(self.inventory_domain, PublishedInputDomain):
            return self.as_input_file(self.inventory_domain.url_fragment())
        elif isinstance(self.inventory_domain, str):
            return self.as_input_file(self.inventory_domain)
        else:
            raise TypeError("Could not interpret the 'inventory_domain' field")

    @property
    def output_domain_file(self):
        """Get the filename of the output domain"""
        return self.as_output_file(self.output_domain)


def load_config_from_env(**overrides: typing.Any) -> PriorConfig:
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
        # TODO: Log?
        input_domain = env.str("DOMAIN")

    options = dict(
        remote=env("PRIOR_REMOTE"),
        input_path=env.path("INPUTS", "data/inputs"),
        output_path=env.path("OUTPUTS", "data/outputs"),
        intermediates_path=env.path("INTERMEDIATES", "data/processed"),
        input_domain=input_domain,
        output_domain=env.str("OUTPUT_DOMAIN", "out-om-domain-info.nc"),
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
