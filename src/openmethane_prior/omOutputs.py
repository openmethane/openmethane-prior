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

import os

import numpy as np
import numpy.typing as npt
import xarray as xr

from openmethane_prior import omInputs
from openmethane_prior.omUtils import getenv, secsPerYear

intermediatesPath = getenv("INTERMEDIATES")
outputsPath = getenv("OUTPUTS")
domainFilename = getenv("DOMAIN")

landuseReprojectionPath = os.path.join(intermediatesPath, "land-use.tif")
ntlReprojectionPath = os.path.join(intermediatesPath, "night-time-lights.tif")
domainOutputPath = os.path.join(outputsPath, f"out-{domainFilename}")
domainJSONOutputPath = os.path.join(outputsPath, "om-domain.json")
geoJSONOutputPath = os.path.join(outputsPath, "om-prior.json")

coordNames = ["TSTEP", "LAY", "ROW", "COL"]


def convert_to_timescale(emission):
    """Convert a gridded emission dataset in kgs/cell/year to kgs/m2/s"""
    di = omInputs.domainXr

    domain_cell_area_m2 = di.DX * di.DY
    return emission / domain_cell_area_m2 / secsPerYear


def write_layer(
    layer_name: str, layer_data: xr.DataArray | npt.ArrayLike, direct_set: bool = False
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

    datapath = domainOutputPath if os.path.exists(domainOutputPath) else omInputs.domainPath
    with xr.open_dataset(datapath) as dss:
        ds = dss.load()
    # if this is a xr dataArray just include it
    if direct_set:
        ds[layer_name] = layer_data
    else:
        # we're about to alter the input so copy first
        copy = layer_data.copy()
        # coerce to four dimensions if it's not
        for i in range(layer_data.ndim, 4):
            copy = np.expand_dims(copy, 0)  # should now have four dimensions
        ds[layer_name] = (coordNames[:], copy)
    ds.to_netcdf(domainOutputPath)


def sumLayers():
    """
    Calculate the total methane emissions from the individual layers and write to the output file.

    This adds the `OCH4_TOTAL` variable to the output file.
    """
    layers = omInputs.omLayers

    if os.path.exists(domainOutputPath):
        with xr.open_dataset(domainOutputPath) as dss:
            ds = dss.load()

        # now check to find largest shape because we'll broadcast everything else to that
        summedSize = 0
        for layer in layers:
            layerName = f"OCH4_{layer.upper()}"

            if layerName in ds:
                if ds[layerName].size > summedSize:
                    summedShape = ds[layerName].shape
                    summedSize = ds[layerName].size

        summed = None
        for layer in layers:
            layerName = f"OCH4_{layer.upper()}"

            if layerName in ds:
                if summed is None:
                    summed = np.zeros(summedShape)
                summed += ds[layerName].values  # it will broadcast time dimensions of 1 correctly

        if summed is not None:
            ds["OCH4_TOTAL"] = (["date", "LAY", *coordNames[-2:]], summed)
            ds.to_netcdf(domainOutputPath)
