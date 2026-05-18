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
import pathlib
import pyproj
from typing import Self
import xarray as xr

from .create_grid import create_grid_from_dataset
from .grid import Grid


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

    @classmethod
    def from_file(cls, file_path: str | pathlib.Path) -> Self:
        """Open a domain NetCDF and build a Domain."""
        domain_ds = xr.open_dataset(file_path)
        grid = create_grid_from_dataset(domain_ds)
        return cls(dataset=domain_ds, grid=grid)
