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
import attrs
import os
import pathlib
import pyproj
import xarray as xr

from .create_grid import create_grid_from_domain, create_grid_from_mcip
from .grid import Grid
from ..data_manager.source import ConfiguredDataSource, DataSource
from ..utils import is_url


@attrs.frozen
class Domain:
    """A parsed domain: the underlying xarray Dataset and its Grid."""

    dataset: xr.Dataset
    grid: Grid

    @property
    def projection(self) -> pyproj.Proj:
        return self.grid.projection

    @property
    def crs(self) -> pyproj.CRS:
        return self.grid.projection.crs


def parse_domain(source: ConfiguredDataSource) -> Domain:
    """Open a domain NetCDF and build a Domain.

    Handles both CF-convention domain files and the legacy MCIP format.
    """
    domain_ds = xr.open_dataset(source.asset_path)
    if "Conventions" in domain_ds.attrs:
        grid = create_grid_from_domain(domain_ds)
    else:
        grid = create_grid_from_mcip(
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
    return Domain(dataset=domain_ds, grid=grid)


def make_domain_source(name: str, url_or_path: str | pathlib.Path) -> DataSource:
    """Build a DataSource for a domain file.

    Accepts either a URL (fetched into the data_path with the URL basename
    as the local file name), an absolute local path, or a relative path
    interpreted against the data_path.
    """
    url_or_path_str = str(url_or_path)
    if is_url(url_or_path_str):
        return DataSource(
            name=name,
            url=url_or_path_str,
            file_path=os.path.basename(url_or_path_str),
            parse=parse_domain,
        )
    return DataSource(
        name=name,
        file_path=url_or_path_str,
        parse=parse_domain,
    )
