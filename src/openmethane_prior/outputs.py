#
# Copyright 2023 The Superpower Institute Ltd.
#
# This file is part of OpenMethane.
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
"""Output handling"""

import pathlib

import numpy as np
import numpy.typing as npt
import xarray as xr

from openmethane_prior.config import PriorConfig
from openmethane_prior.layers import layer_names
from openmethane_prior.utils import SECS_PER_YEAR

coordNames = ["TSTEP", "LAY", "ROW", "COL"]


def convert_to_timescale(emission, cell_area):
    """Convert a gridded emission dataset in kgs/cell/year to kgs/m2/s"""
    return emission / cell_area / SECS_PER_YEAR


def write_layer(
    config: PriorConfig,
    layer_name: str,
    layer_data: xr.DataArray | npt.ArrayLike,
    direct_set: bool = False,
):
    """
    Write a layer to the output file

    Parameters
    ----------
    layer_name
        Name
    layer_data
        Data to write to file

        This could be a xarray Dataset
    direct_set
        If True, write the data to the output file without processing
        If False, coerce to the layer_data to 4d if it isn't already
    """
    print(f"Writing emissions data for {layer_name}")

    output_path = config.output_domain_file
    input_path = config.input_domain_file

    datapath = output_path if output_path.exists() else input_path

    ds = xr.load_dataset(datapath)

    # i
    # f this is a xr dataArray just include it
    if direct_set:
        ds[layer_name] = layer_data
    else:
        # we're about to alter the input so copy first
        copy = layer_data.copy()
        # coerce to four dimensions if it's not
        for i in range(layer_data.ndim, 4):
            copy = np.expand_dims(copy, 0)  # should now have four dimensions
        ds[layer_name] = (coordNames[:], copy)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(output_path)


def sum_layers(output_path: pathlib.Path):
    """
    Calculate the total methane emissions from the individual layers and write to the output file.

    This adds the `OCH4_TOTAL` variable to the output file.
    """
    if not output_path.exists():
        raise FileNotFoundError("Output file does not exist")

    ds = xr.load_dataset(output_path)

    # now check to find largest shape because we'll broadcast everything else to that
    summedSize = 0
    for layer in layer_names:
        layerName = f"OCH4_{layer.upper()}"

        if layerName in ds:
            if ds[layerName].size > summedSize:
                summedShape = ds[layerName].shape
                summedSize = ds[layerName].size

    summed = None
    for layer in layer_names:
        layerName = f"OCH4_{layer.upper()}"

        if layerName in ds:
            if summed is None:
                summed = np.zeros(summedShape)
            summed += ds[layerName].values  # it will broadcast time dimensions of 1 correctly

    if summed is not None:
        ds["OCH4_TOTAL"] = (["date", "LAY", *coordNames[-2:]], summed)
        ds.to_netcdf(output_path)
