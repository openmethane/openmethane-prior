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

"""Processing industrial stationary transport emissions"""

import geopandas
import numpy as np
import pandas as pd
import rioxarray as rxr
import xarray as xr
from openmethane_prior.config import PriorConfig, load_config_from_env
from openmethane_prior.outputs import (
    convert_to_timescale,
    sum_layers,
    write_layer,
)


def _find_grid(data, totalSize, gridSize):
    return np.floor((data + totalSize / 2) / gridSize)


def processEmissions(config: PriorConfig):
    """
    Process emissions for Industrial, Stationary and Transport

    Writes layers into the output file
    """
    print("processEmissions for Industrial, Stationary and Transport")

    sectorsUsed = ["industrial", "stationary", "transport"]

    _ntlData = rxr.open_rasterio(
        config.as_intermediate_file(config.layer_inputs.ntl_path), masked=True
    )

    print("Clipping night-time lights data to Australian land border")
    ausf = geopandas.read_file(config.as_input_file(config.layer_inputs.aus_shapefile_path))
    ausf_rp = ausf.to_crs(config.crs)
    ntlData = _ntlData.rio.clip(ausf_rp.geometry.values, ausf_rp.crs)

    # Add together the intensity of the 3 channels for a total intensity per pixel
    numNtltData = np.nan_to_num(ntlData)
    ntlt = np.nan_to_num(numNtltData[0] + numNtltData[1] + numNtltData[2])

    # Sum all pixel intensities
    ntltTotal = np.sum(ntlt)

    # Divide each pixel intensity by the total to get a scaled intensity per pixel
    ntltScalar = ntlt / ntltTotal

    sectorData = pd.read_csv(
        config.as_input_file(config.layer_inputs.sectoral_emissions_path)
    ).to_dict(orient="records")[0]
    ntlIndustrial = ntltScalar * (sectorData["industrial"] * 1e9)
    ntlStationary = ntltScalar * (sectorData["stationary"] * 1e9)
    ntlTransport = ntltScalar * (sectorData["transport"] * 1e9)

    # Load domain
    domain_ds = config.domain_dataset()
    landmask = domain_ds["LANDMASK"][:]

    _, lmy, lmx = landmask.shape
    ww = domain_ds.DX * lmx
    hh = domain_ds.DY * lmy

    print("Mapping night-time lights grid to domain grid")
    xDomain = xr.apply_ufunc(_find_grid, ntlData.x, ww, domain_ds.DX).values.astype(int)
    yDomain = xr.apply_ufunc(_find_grid, ntlData.y, hh, domain_ds.DY).values.astype(int)

    # xDomain = np.floor((ntlData.x + ww / 2) / domain_ds.DX).astype(int)
    # yDomain = np.floor((ntlData.y + hh / 2) / domain_ds.DY).astype(int)

    methane = {}
    for sector in sectorsUsed:
        methane[sector] = np.zeros(domain_ds["LANDMASK"].shape)

    litPixels = np.argwhere(ntlt > 0)
    ignored = 0

    for y, x in litPixels:
        try:
            methane["industrial"][0][yDomain[y]][xDomain[x]] += ntlIndustrial[y][x]
            methane["stationary"][0][yDomain[y]][xDomain[x]] += ntlStationary[y][x]
            methane["transport"][0][yDomain[y]][xDomain[x]] += ntlTransport[y][x]
        except Exception as e:
            print(e)
            ignored += 1

    print(f"{ignored} lit pixels were ignored")

    for sector in sectorsUsed:
        write_layer(
            config,
            f"OCH4_{sector.upper()}",
            convert_to_timescale(methane[sector], config.domain_cell_area),
        )


if __name__ == "__main__":
    config = load_config_from_env()
    processEmissions(config)
    sum_layers(config.output_domain_file)
