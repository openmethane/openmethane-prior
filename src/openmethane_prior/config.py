import pathlib
from functools import cache

import attrs
import pyproj
import xarray as xr
from environs import Env


@attrs.frozen()
class LayerInputs:
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
    input_path: pathlib.Path
    output_path: pathlib.Path
    intermediates_path: pathlib.Path

    layer_inputs: LayerInputs

    # CMAQ specific paths
    cro_file: pathlib.Path
    dot_file: pathlib.Path
    geometry_file: pathlib.Path

    def as_input_file(self, name: str | pathlib.Path) -> pathlib.Path:
        return self.input_path / name

    def as_intermediate_file(self, name: str | pathlib.Path) -> pathlib.Path:
        return self.intermediates_path / name

    def as_output_file(self, name: str | pathlib.Path) -> pathlib.Path:
        return self.output_path / name

    @cache
    def domain_dataset(self):
        expected_filename = self.as_input_file(self.domain)
        if not expected_filename.exists():
            raise ValueError(f"Missing domain file: {expected_filename}")
        return xr.load_dataset(expected_filename)

    @cache
    def domain_projection(self):
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
        return self.domain_projection().crs

    @property
    def domain_cell_area(self):
        ds = self.domain_dataset()
        return ds.DX * ds.DY

    @property
    def input_domain_file(self):
        return self.as_input_file(self.domain)

    @property
    def output_domain_file(self):
        return self.as_output_file(f"out-{self.domain}")


def load_config_from_env() -> PriorConfig:
    env = Env(
        expand_vars=True,
    )
    env.read_env(verbose=True)

    return PriorConfig(
        domain=env("DOMAIN"),
        input_path=env.path("INPUT_PATH", "data/inputs"),
        output_path=env.path("OUTPUT_PATH", "data/outputs"),
        intermediates_path=env.path("INTERMEDIATES_PATH", "data/inputs"),
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
