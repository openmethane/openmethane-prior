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

"""Download and process GFAS data

This downloads files from [ADS](https://atmosphere.copernicus.eu/data).
See the project readme for more information about configuring
the required credentials.
"""

import bisect
import datetime
import itertools
import netCDF4 as nc
import os
import pathlib

import cdsapi
import numpy as np
import xarray as xr
from openmethane_prior.sector.config import PriorSectorConfig
from shapely import geometry

from openmethane_prior.config import PriorConfig, load_config_from_env, parse_cli_to_env
from openmethane_prior.outputs import add_ch4_total, add_sector, create_output_dataset, write_output_dataset
from openmethane_prior.sector.sector import SectorMeta
from openmethane_prior.utils import (
    area_of_rectangle_m2,
    load_zipped_pickle,
    redistribute_spatially,
    save_zipped_pickle,
)
import openmethane_prior.logger as logger

logger = logger.get_logger(__name__)

sector_meta = SectorMeta(
    name="fire",
    emission_category="natural",
    cf_standard_name="fires",
)

def download_GFAS(
    start_date: datetime.date,
    end_date: datetime.date,
    file_name: str | pathlib.Path,
):
    """
    Download GFAS methane between start and end date, returning the filename
    of the retrieved data.
    """
    dateString = start_date.strftime("%Y-%m-%d") + "/" + end_date.strftime("%Y-%m-%d")

    downloadPath = pathlib.Path(file_name);
    downloadPath.parent.mkdir(parents=True, exist_ok=True)

    c = cdsapi.Client(progress=False)

    c.retrieve(
        "cams-global-fire-emissions-gfas",
        {
            "date": dateString,
            "format": "netcdf",
            "variable": [
                "wildfire_flux_of_methane",
            ],
        },
        file_name,
    )
    return file_name


def processEmissions(sector_config: PriorSectorConfig, prior_ds: xr.Dataset, forceUpdate: bool = False, **kwargs):  # noqa: PLR0915
    """
    Remap GFAS fire emissions to the CMAQ domain
    """
    config = sector_config.prior_config

    gfas_file = download_GFAS(
        config.start_date, config.end_date, file_name=config.as_intermediate_file("gfas-download.nc")
    )
    gfas_ds = nc.Dataset(gfas_file, "r")

    # dates are labelled at midnight at end of chosen day (hence looks like next day), subtract one day to fix
    oneDay = np.timedelta64(1, "D")
    gfasTimesRaw = nc.num2date(gfas_ds.variables["valid_time"], gfas_ds.variables["valid_time"].getncattr("units"))
    gfasTimes = [np.datetime64(t) - oneDay for t in gfasTimesRaw]

    latGfas = np.around(np.float64(gfas_ds.variables["latitude"][:]), 3)
    latGfas = latGfas[::-1]  # they're originally north-south, we want them south north
    lonGfas = np.around(np.float64(gfas_ds.variables["longitude"][:]), 3)
    dlatGfas = latGfas[0] - latGfas[1]
    dlonGfas = lonGfas[1] - lonGfas[0]
    lonGfas_edge = np.zeros(len(lonGfas) + 1)
    lonGfas_edge[0:-1] = lonGfas - dlonGfas / 2.0
    lonGfas_edge[-1] = lonGfas[-1] + dlonGfas / 2.0
    lonGfas_edge = np.around(lonGfas_edge, 2)

    latGfas_edge = np.zeros(len(latGfas) + 1)
    latGfas_edge[0:-1] = latGfas + dlatGfas / 2.0
    latGfas_edge[-1] = latGfas[-1] - dlatGfas / 2.0
    latGfas_edge = np.around(latGfas_edge, 2)

    nlonGfas = len(lonGfas)
    nlatGfas = len(latGfas)

    logger.debug("Calculate grid cell areas for the GFAS grid")
    GFASAreas = np.zeros((nlatGfas, nlonGfas))
    # take advantage of  regular grid to compute areas equal for each gridbox at same latitude
    for iy in range(nlatGfas):
        GFASAreas[iy, :] = (
            area_of_rectangle_m2(
                latGfas_edge[iy], latGfas_edge[iy + 1], lonGfas_edge[0], lonGfas_edge[-1]
            )
            / lonGfas.size
        )
    # now collect some domain information
    domain_grid = config.domain_grid()

    indxPath = config.as_intermediate_file("GFAS_ind_x.p.gz")
    indyPath = config.as_intermediate_file("GFAS_ind_y.p.gz")
    coefsPath = config.as_intermediate_file("GFAS_ind_coefs.p.gz")

    if (
        os.path.exists(indxPath)
        and os.path.exists(indyPath)
        and os.path.exists(coefsPath)
        and (not forceUpdate)
    ):
        ind_x = load_zipped_pickle(indxPath)
        ind_y = load_zipped_pickle(indyPath)
        coefs = load_zipped_pickle(coefsPath)
        ##
        domShape = []
        domShape.append(domain_grid.shape)
    else:
        ind_x = []
        ind_y = []
        coefs = []
        count = []
        domShape = []

        ind_x.append([])
        ind_y.append([])
        coefs.append([])

        cell_bounds_lon, cell_bounds_lat = domain_grid.cell_bounds_lonlat()

        domShape.append(domain_grid.shape)

        count2 = np.zeros(domain_grid.shape, dtype=np.float32)

        for i, j in itertools.product(range(domain_grid.shape[0]), range(domain_grid.shape[1])):
            IND_X = []
            IND_Y = []
            COEFS = []

            xvals = cell_bounds_lon[i, j]
            yvals = cell_bounds_lat[i, j]
            CMAQ_gridcell = geometry.Polygon(zip(xvals, yvals))

            xmin = np.min(xvals)
            xmax = np.max(xvals)
            ymin = np.min(yvals)
            ymax = np.max(yvals)

            ixminl = bisect.bisect_right(lonGfas_edge, xmin)
            ixmaxr = bisect.bisect_right(lonGfas_edge, xmax)
            iyminl = bisect.bisect_right(latGfas_edge, ymin)
            iymaxr = bisect.bisect_right(latGfas_edge, ymax)

            for ix, iy in itertools.product(
                range(max(0, ixminl - 1), min(nlonGfas, ixmaxr)),
                range(max(0, iyminl - 1), min(nlatGfas, iymaxr)),
            ):
                gfas_gridcell = geometry.box(
                    lonGfas_edge[ix], latGfas_edge[iy], lonGfas_edge[ix + 1], latGfas_edge[iy + 1]
                )
                if CMAQ_gridcell.intersects(gfas_gridcell):
                    intersection = CMAQ_gridcell.intersection(gfas_gridcell)
                    weight2 = (
                        intersection.area / gfas_gridcell.area
                    )  ## fraction of GFAS cell covered
                    count2[i, j] += weight2
                    IND_X.append(ix)
                    IND_Y.append(iy)
                    COEFS.append(weight2)
            ind_x.append(IND_X)
            ind_y.append(IND_Y)
            # COEFS = np.array(COEFS)
            # COEFS = COEFS / COEFS.sum()
            coefs.append(COEFS)
        count.append(count2)
        ##
        save_zipped_pickle(ind_x, indxPath)
        save_zipped_pickle(ind_y, indyPath)
        save_zipped_pickle(coefs, coefsPath)

    resultNd = []  # will become ndarray
    dates = []
    cmaq_areas = np.ones(domain_grid.shape) * domain_grid.cell_area  # all grid cells equal area

    for i in range(len(gfasTimes)):
        dates.append(gfasTimes[i])
        subset = gfas_ds["ch4fire"][i, ...]
        subset = subset[::-1, :]  # they're listed north-south, we want them south north
        resultNd.append(
            redistribute_spatially(domain_grid.shape, ind_x, ind_y, coefs, subset, GFASAreas, cmaq_areas)
        )
    resultNd = np.array(resultNd)
    resultNd = np.expand_dims(resultNd, 1)  # adding single vertical dimension
    resultXr = xr.DataArray(
        resultNd,
        coords={
            "time": dates,
            "vertical": np.array([1]),
            "y": np.arange(resultNd.shape[-2]),
            "x": np.arange(resultNd.shape[-1]),
        },
    )
    add_sector(
        prior_ds=prior_ds,
        sector_data=resultXr,
        sector_meta=sector_meta,
    )
    return resultNd


if __name__ == "__main__":
    parse_cli_to_env()
    config = load_config_from_env()
    data_manager = DataManager(data_path=config.input_path)
    sector_config = PriorSectorConfig(prior_config=config, data_manager=data_manager)

    ds = create_output_dataset(config)
    processEmissions(sector_config, ds)
    add_ch4_total(ds)
    write_output_dataset(config, ds)
