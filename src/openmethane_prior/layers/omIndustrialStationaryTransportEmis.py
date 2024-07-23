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

def remap_raster( input_field: xr.core.dataarray.DataArray,\
                  config: PriorConfig,\
                  AREA_OR_POINT = 'AREA') -> np.ndarray:
    """ maps a rasterio dataset onto the domain defined by config.
    returns np.ndarray """
    result = np.zeros( config.domain_dataset()['LAT'].shape[-2:]) # any field will do and select only horizontal dims
    count = np.zeros_like( result)
    # we accumulate values from each high-res grid in the raster onto our domain then divide by the number
    # our criterion is that the central point in the high-res lies inside the cell defined on the grid
    # get input resolutions, these are not retained in this data structure despite presence in underlying tiff file
    # the following needs .to_numpy() because
    #subtracting xarray matches coordinates, not what we want
    delta_lon = (input_field.x.to_numpy()[1:] -input_field.x.to_numpy()[0:-1]).mean()
    delta_lat = (input_field.y.to_numpy()[1:] -input_field.y.to_numpy()[0:-1]).mean()
    # output resolutions and extents
    delta_x = config.domain_dataset().XCELL
    lmx = result.shape[-1]
    delta_y = config.domain_dataset().YCELL
    lmy = result.shape[-2]
    input_field_as_array = input_field.to_numpy()
    llc_x, llc_y = config.llc_xy() # lower left corner in x,y coords
    # the raster is defined lat-lon so we need to reproject each row separately onto the LCC grid
    for j in range( input_field.y.size):
        lons = input_field.x.to_numpy()
        lat = input_field.y.item(j)
        lats = np.array([lat]).repeat( lons.size) # proj needs lats,lons same size
        # correct for point being corner or centre of box, we want centre
        if AREA_OR_POINT == 'Area':
            lons += delta_lon/2.
            lats += delta_lat/2

        x, y = config.domain_projection()(lons, lats)
        # calculate indices  assuming regular grid
        ix = np.floor((x -llc_x) / delta_x).astype('int')
        iy = np.floor((y -llc_y) / delta_y).astype('int')
        # input domain is bigger so mask indices out of range
        mask = ( ix >= 0) & (ix < lmx) & (iy >= 0) & (iy < lmy)
        if mask.any():
            # the following needs to use .at method since iy,ix indices may be repeated and we need to acumulate 
            np.add.at(result, (iy[mask], ix[mask]), input_field_as_array[j, mask])
            np.add.at(count, (iy[mask], ix[mask]),  1)
    has_vals = count > 0
    result[ has_vals] /= count[ has_vals]
    return result


def processEmissions(config: PriorConfig):
    """
    Process emissions for Industrial, Stationary and Transport

    Writes layers into the output file
    """
    print("processEmissions for Industrial, Stationary and Transport")

    sectorsUsed = ["industrial", "stationary", "transport"]

    ntlData = rxr.open_rasterio(
        config.as_input_file(config.layer_inputs.ntl_path), masked=True
    )
    # filter nans
    np.nan_to_num(ntlData, copy=False)
    ntlt = ntlData.sum( axis=0)

    # Sum all pixel intensities
    ntltTotal = np.sum(ntlt)

    # Divide each pixel intensity by the total to get a scaled intensity per pixel
    ntlt /= ntltTotal
    om_ntlt = remap_raster(ntlt, config, AREA_OR_POINT = ntlData.AREA_OR_POINT)
    # we want proportions of total for scaling emissions
    ntltScalar = om_ntlt/om_ntlt.sum()
    sectorData = pd.read_csv(
        config.as_input_file(config.layer_inputs.sectoral_emissions_path)
    ).to_dict(orient="records")[0]
    methane = {}
    for sector in sectorsUsed:
        methane[sector] = ntltScalar * sectorData[sector] * 1e9
        write_layer(
            config.output_domain_file,
            f"OCH4_{sector.upper()}",
            convert_to_timescale(methane[sector], config.domain_cell_area),
        )


if __name__ == "__main__":
    config = load_config_from_env()
    processEmissions(config)
    sum_layers(config.output_domain_file)
