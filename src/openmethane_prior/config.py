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

    These files are downloaded to the `input_path` directory via `scripts/omDownloadInputs.py`.
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


@attrs.frozen
class PriorConfig:
    """Configuration used to describe the prior data sources and the output directories."""

    domain: str
    remote: str
    input_path: pathlib.Path
    output_path: pathlib.Path
    intermediates_path: pathlib.Path

    layer_inputs: LayerInputs

    # CMAQ specific paths
    cro_file: pathlib.Path
    dot_file: pathlib.Path
    geometry_file: pathlib.Path

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
        return xr.load_dataset(self.input_domain_file)

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
        """Get the filename of the input domain"""
        return self.as_input_file(self.domain)

    @property
    def output_domain_file(self):
        """Get the filename of the output domain"""
        return self.as_output_file(f"out-{self.domain}")


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

    options = dict(
        domain=env("DOMAIN"),
        remote=env("PRIOR_REMOTE"),
        input_path=env.path("INPUT_PATH", "data/inputs"),
        output_path=env.path("OUTPUT_PATH", "data/outputs"),
        intermediates_path=env.path("INTERMEDIATES_PATH", "data/processed"),
        layer_inputs=LayerInputs(
            electricity_path=env.path("ELECTRICITY_PATH"),
            oil_gas_path=env.path("OIL_GAS_PATH"),
            coal_path=env.path("COAL_PATH"),
            land_use_path=env.path("LAND_USE_PATH"),
            sectoral_emissions_path=env.path("SECTORAL_EMISSIONS_PATH"),
            sectoral_mapping_path=env.path("SECTORAL_MAPPING_PATH"),
            ntl_path=env.path("NTL_PATH"),
            aus_shapefile_path=env.path("AUS_SHAPEFILE_PATH"),
            livestock_path=env.path("LIVESTOCK_PATH"),
            termite_path=env.path("TERMITE_PATH"),
            wetland_path=env.path("WETLAND_PATH"),
        ),
        cro_file=env.path("CRO_FILE"),
        dot_file=env.path("DOT_FILE"),
        geometry_file=env.path("GEOMETRY_FILE"),
    )

    return PriorConfig(**{**options, **overrides})
