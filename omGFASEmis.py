"""
omGFASEmis.py

Copyright 2023 The Superpower Institute Ltd
Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

import argparse
import bisect
import datetime
import itertools
import os

import cdsapi
import netCDF4 as nc
import numpy as np
import omUtils
import xarray as xr
from omInputs import domainXr
from omOutputs import intermediatesPath, sumLayers, writeLayer
from shapely import geometry

GFASDownloadPath = os.path.join(intermediatesPath, "gfas-download.nc")


def downloadGFAS(startDate, endDate, fileName=GFASDownloadPath):
    """Download GFAS methane between two dates startDate and endDate, returns nothing"""
    dateString = startDate.strftime("%Y-%m-%d") + "/" + endDate.strftime("%Y-%m-%d")
    c = cdsapi.Client()

    c.retrieve(
        "cams-global-fire-emissions-gfas",
        {
            "date": dateString,
            "format": "netcdf",
            "variable": [
                "wildfire_flux_of_methane",
            ],
        },
        fileName,
    )
    return fileName


def processEmissions(startDate, endDate, forceUpdate=False):
    """Function to remap GFAS fire emissions to the CMAQ domain

    Args:
        startDate, endDate: the date range (datetime objects)
        forceUpdate: If True, ignore cached grid weights

    Returns
    -------
        Nothing
    """
    GFASfile = downloadGFAS(startDate, endDate)
    ncin = nc.Dataset(GFASfile, "r", format="NETCDF3")
    latGfas = np.around(np.float64(ncin.variables["latitude"][:]), 3)
    latGfas = latGfas[::-1]  # they're originally north-south, we want them south north
    lonGfas = np.around(np.float64(ncin.variables["longitude"][:]), 3)
    dlatGfas = latGfas[0] - latGfas[1]
    dlonGfas = lonGfas[1] - lonGfas[0]
    lonGfas_edge = np.zeros(len(lonGfas) + 1)
    lonGfas_edge[0:-1] = lonGfas - dlonGfas / 2.0
    lonGfas_edge[-1] = lonGfas[-1] + dlonGfas / 2.0
    lonGfas_edge = np.around(lonGfas_edge, 2)
    gfasTimes = nc.num2date(ncin.variables["time"][:], ncin.variables["time"].getncattr("units"))

    latGfas_edge = np.zeros(len(latGfas) + 1)
    latGfas_edge[0:-1] = latGfas + dlatGfas / 2.0
    latGfas_edge[-1] = latGfas[-1] - dlatGfas / 2.0
    latGfas_edge = np.around(latGfas_edge, 2)

    nlonGfas = len(lonGfas)
    nlatGfas = len(latGfas)

    print("Calculate grid cell areas for the GFAS grid")
    GFASAreas = np.zeros((nlatGfas, nlonGfas))
    # take advantage of  regular grid to compute areas equal for each gridbox at same latitude
    for iy in range(nlatGfas):
        GFASAreas[iy, :] = (
            omUtils.area_of_rectangle_m2(
                latGfas_edge[iy], latGfas_edge[iy + 1], lonGfas_edge[0], lonGfas_edge[-1]
            )
            / lonGfas.size
        )
    # now collect some domain information
    LATD = domainXr["LATD"][:].values.squeeze()
    LOND = domainXr["LOND"].values.squeeze()
    LAT = domainXr.variables["LAT"].values.squeeze()
    cmaqArea = domainXr.XCELL * domainXr.YCELL

    indxPath = f"{intermediatesPath}/GFAS_ind_x.p.gz"
    indyPath = f"{intermediatesPath}/GFAS_ind_y.p.gz"
    coefsPath = f"{intermediatesPath}/GFAS_coefs.p.gz"

    if (
        os.path.exists(indxPath)
        and os.path.exists(indyPath)
        and os.path.exists(coefsPath)
        and (not forceUpdate)
    ):
        ind_x = omUtils.load_zipped_pickle(indxPath)
        ind_y = omUtils.load_zipped_pickle(indyPath)
        coefs = omUtils.load_zipped_pickle(coefsPath)
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
                    weight1 = intersection.area / CMAQ_gridcell.area  ## fraction of CMAQ cell covered
                    weight2 = intersection.area / gfas_gridcell.area  ## fraction of GFAS cell covered
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
        omUtils.save_zipped_pickle(ind_x, indxPath)
        omUtils.save_zipped_pickle(ind_y, indyPath)
        omUtils.save_zipped_pickle(coefs, coefsPath)

    resultNd = []  # will become ndarray
    dates = []
    cmaqAreas = np.ones(LAT.shape) * cmaqArea  # all grid cells equal area

    for i in range(gfasTimes.size):
        dates.append(startDate + datetime.timedelta(days=i))
        subset = ncin["ch4fire"][i, ...]
        subset = subset[::-1, :]  # they're listed north-south, we want them south north
        resultNd.append(
            omUtils.redistribute_spatially(LAT.shape, ind_x, ind_y, coefs, subset, GFASAreas, cmaqAreas)
        )
    resultNd = np.array(resultNd)
    resultNd = np.expand_dims(resultNd, 1)  # adding dummy layer dimension
    resultXr = xr.DataArray(
        resultNd,
        coords={
            "date": dates,
            "LAY": np.array([1]),
            "y": np.arange(resultNd.shape[-2]),
            "x": np.arange(resultNd.shape[-1]),
        },
    )
    writeLayer("OCH4_FIRE", resultXr, True)
    return resultNd


def testGFASEmis(
    startDate, endDate, **kwargs
):  # test totals for GFAS emissions between original and remapped
    remapped = processEmissions(startDate, endDate, **kwargs)
    GFASfile = "download.nc"
    ncin = nc.Dataset(GFASfile, "r", format="NETCDF3")
    latGfas = np.around(np.float64(ncin.variables["latitude"][:]), 3)
    lonGfas = np.around(np.float64(ncin.variables["longitude"][:]), 3)
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

    areas = np.zeros((nlatGfas, nlonGfas))
    # take advantage of  regular grid to compute areas equal for each gridbox at same latitude
    for iy in range(nlatGfas):
        areas[iy, :] = (
            omUtils.area_of_rectangle_m2(
                latGfas_edge[iy], latGfas_edge[iy + 1], lonGfas_edge[0], lonGfas_edge[-1]
            )
            / lonGfas.size
        )
    LATD = domainXr.variables["LATD"].values.squeeze()
    LOND = domainXr.variables["LOND"].values.squeeze()
    indLat = (latGfas > LATD.min()) & (latGfas < LATD.max())
    indLon = (lonGfas > LOND.min()) & (lonGfas < LOND.max())
    gfasCH4 = ncin["ch4fire"][...]
    inds = np.ix_(indLat, indLon)
    gfasTotals = [np.tensordot(gfasCH4[i][inds], areas[inds]) for i in range(gfasCH4.shape[0])]

    remappedTotals = remapped.sum(axis=(1, 2))
    for t in zip(gfasTotals, remappedTotals):
        print(t)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate the prior methane emissions estimate for OpenMethane"
    )
    parser.add_argument(
        "startDate",
        type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"),
        help="Start date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "endDate",
        type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"),
        help="end date in YYYY-MM-DD format",
    )
    args = parser.parse_args()
    processEmissions(args.startDate, args.endDate)
    sumLayers()
