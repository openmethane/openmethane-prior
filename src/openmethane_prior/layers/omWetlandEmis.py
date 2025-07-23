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

"""Processing wetland emissions"""

import bisect
import itertools
import os

import netCDF4 as nc
import numpy as np
import xarray as xr
from shapely import geometry

from openmethane_prior.config import PriorConfig, load_config_from_env, parse_cli_to_env
from openmethane_prior.outputs import add_ch4_total, add_sector, create_output_dataset, write_output_dataset
from openmethane_prior.utils import (
    area_of_rectangle_m2,
    load_zipped_pickle,
    redistribute_spatially,
    save_zipped_pickle,
)


def make_wetland_climatology(config: PriorConfig, forceUpdate: bool = False):  # noqa: PLR0915
    """
    Remap wetland emissions to the CMAQ domain

    Parameters
    ----------
    forceUpdate
        If True, always recalculate grid mapping indices

    Returns
    -------
        Array containing the processed results
    """
    ncin = nc.Dataset(config.as_input_file(config.layer_inputs.wetland_path), "r")
    latWetland = np.around(np.float64(ncin.variables["lat"][:]), 3)
    lonWetland = np.around(np.float64(ncin.variables["lon"][:]), 3)
    dlatWetland = latWetland[0] - latWetland[1]
    dlonWetland = lonWetland[1] - lonWetland[0]
    lonWetland_edge = np.zeros(len(lonWetland) + 1)
    lonWetland_edge[0:-1] = lonWetland - dlonWetland / 2.0
    lonWetland_edge[-1] = lonWetland[-1] + dlonWetland / 2.0
    lonWetland_edge = np.around(lonWetland_edge, 2)

    latWetland_edge = np.zeros(len(latWetland) + 1)
    latWetland_edge[0:-1] = latWetland + dlatWetland / 2.0
    latWetland_edge[-1] = latWetland[-1] - dlatWetland / 2.0
    latWetland_edge = np.around(latWetland_edge, 2)

    nlonWetland = len(lonWetland)
    nlatWetland = len(latWetland)

    wetlandAreas = np.zeros((nlatWetland, nlonWetland))
    # take advantage of  regular grid to compute areas equal for each gridbox at same latitude
    for iy in range(nlatWetland):
        wetlandAreas[iy, :] = (
            area_of_rectangle_m2(
                latWetland_edge[iy],
                latWetland_edge[iy + 1],
                lonWetland_edge[0],
                lonWetland_edge[-1],
            )
            / lonWetland.size
        )
    # now collect some domain information
    domain_ds = config.domain_dataset()
    LAT = domain_ds.variables["LAT"].values.squeeze()
    cmaqArea = domain_ds.XCELL * domain_ds.YCELL

    indxPath = config.as_intermediate_file("WETLAND_ind_x.p.gz")
    indyPath = config.as_intermediate_file("WETLAND_ind_y.p.gz")
    coefsPath = config.as_intermediate_file("WETLAND_ind_coefs.p.gz")

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
        domShape.append(LAT.shape)
    else:
        ind_x = []
        ind_y = []
        coefs = []
        count = []
        domShape = []

        ind_x.append([])
        ind_y.append([])
        coefs.append([])

        LATD = domain_ds.variables["LATD"].values.squeeze()
        LOND = domain_ds.variables["LOND"].values.squeeze()

        domShape.append(LAT.shape)

        count2 = np.zeros(LAT.shape, dtype=np.float32)

        for i, j in itertools.product(range(LAT.shape[0]), range(LAT.shape[1])):
            IND_X = []
            IND_Y = []
            COEFS = []

            xvals = np.array([LOND[i, j], LOND[i, j + 1], LOND[i + 1, j], LOND[i + 1, j + 1]])
            yvals = np.array([LATD[i, j], LATD[i, j + 1], LATD[i + 1, j], LATD[i + 1, j + 1]])

            xy = [
                [LOND[i, j], LATD[i, j]],
                [LOND[i, j + 1], LATD[i, j + 1]],
                [LOND[i + 1, j + 1], LATD[i + 1, j + 1]],
                [LOND[i + 1, j], LATD[i + 1, j]],
            ]
            CMAQ_gridcell = geometry.Polygon(xy)

            xmin = np.min(xvals)
            xmax = np.max(xvals)
            ymin = np.min(yvals)
            ymax = np.max(yvals)

            ixminl = bisect.bisect_right(lonWetland_edge, xmin)
            ixmaxr = bisect.bisect_right(lonWetland_edge, xmax)
            iyminl = bisect.bisect_right(latWetland_edge, ymin)
            iymaxr = bisect.bisect_right(latWetland_edge, ymax)

            for ix, iy in itertools.product(
                range(max(0, ixminl - 1), min(nlonWetland, ixmaxr)),
                range(max(0, iyminl - 1), min(nlatWetland, iymaxr)),
            ):
                Wetland_gridcell = geometry.box(
                    lonWetland_edge[ix],
                    latWetland_edge[iy],
                    lonWetland_edge[ix + 1],
                    latWetland_edge[iy + 1],
                )
                if CMAQ_gridcell.intersects(Wetland_gridcell):
                    intersection = CMAQ_gridcell.intersection(Wetland_gridcell)
                    wetland_frac = (
                        intersection.area / Wetland_gridcell.area
                    )  ## fraction of WETLAND cell covered
                    count2[i, j] += wetland_frac
                    IND_X.append(ix)
                    IND_Y.append(iy)
                    COEFS.append(wetland_frac)
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
    # now build monthly climatology
    flux = ncin["totflux"][...]  # is masked array
    climatology = np.zeros(
        (12, flux.shape[1], flux.shape[2])
    )  # same spatial domain but monthly climatology
    for month in range(12):
        climatology[month, ...] = flux[month::12, ...].mean(
            axis=0
        )  # average over time axis with stride 12
    cmaqAreas = np.ones(LAT.shape) * cmaqArea  # all grid cells equal area
    result = np.zeros((12, LAT.shape[0], LAT.shape[1]))
    for month in range(12):
        result[month, ...] = redistribute_spatially(
            LAT.shape, ind_x, ind_y, coefs, climatology[month, ...], wetlandAreas, cmaqAreas
        )
    ncin.close()
    return np.array(result)


def processEmissions(
    config: PriorConfig,
    prior_ds: xr.Dataset,
    forceUpdate: bool = False,
):
    """
    Process wetland emissions for the given date range
    """
    climatology = make_wetland_climatology(config, forceUpdate=forceUpdate)
    result_nd = []  # will be ndarray once built
    for date in prior_ds["time"].values:
        result_nd.append(climatology[date.month - 1, ...])  # d.month is 1-based

    result_nd = np.array(result_nd)
    result_nd = np.expand_dims(result_nd, 1)  # adding single vertical dimension
    result_xr = xr.DataArray(
        result_nd,
        coords={
            "time": prior_ds["time"].values,
            "vertical": np.array([1]),
            "y": np.arange(result_nd.shape[-2]),
            "x": np.arange(result_nd.shape[-1]),
        },
    )
    add_sector(
        prior_ds=prior_ds,
        sector_name="wetlands",
        sector_data=result_xr,
        sector_standard_name="wetland_biological_processes",
    )
    return result_nd


if __name__ == "__main__":
    parse_cli_to_env()
    config = load_config_from_env()

    ds = create_output_dataset(config)
    processEmissions(config, ds)
    add_ch4_total(ds)
    write_output_dataset(config, ds)
