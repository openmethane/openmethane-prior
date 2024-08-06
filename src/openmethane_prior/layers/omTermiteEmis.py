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

"""Processing termite Methane emissions"""

import bisect
import itertools
import os

import netCDF4 as nc
import numpy as np
from shapely import geometry

from openmethane_prior.config import PriorConfig, load_config_from_env
from openmethane_prior.outputs import sum_layers, write_layer
from openmethane_prior.utils import (
    SECS_PER_YEAR,
    area_of_rectangle_m2,
    load_zipped_pickle,
    redistribute_spatially,
    save_zipped_pickle,
)


def processEmissions(  # noqa: PLR0915
    config: PriorConfig,
    forceUpdate: bool = False,
    **kwargs,
):
    """Remap termite emissions to the CMAQ domain

    Args:
    ----
        forceUpdate
            If True, always recalculate grid mapping indices
        startDate, endDate
            Currently ignored
    """
    ncin = nc.Dataset(config.as_input_file(config.layer_inputs.termite_path), "r")
    latTerm = np.around(np.float64(ncin.variables["lat"][:]), 3)
    latTerm = latTerm[-1::-1]  # we need it south-north
    lonTerm = np.around(np.float64(ncin.variables["lon"][:]), 3)
    dlatTerm = latTerm[0] - latTerm[1]
    dlonTerm = lonTerm[1] - lonTerm[0]
    lonTerm_edge = np.zeros(len(lonTerm) + 1)
    lonTerm_edge[0:-1] = lonTerm - dlonTerm / 2.0
    lonTerm_edge[-1] = lonTerm[-1] + dlonTerm / 2.0
    lonTerm_edge = np.around(lonTerm_edge, 2)

    latTerm_edge = np.zeros(len(latTerm) + 1)
    latTerm_edge[0:-1] = latTerm + dlatTerm / 2.0
    latTerm_edge[-1] = latTerm[-1] - dlatTerm / 2.0
    latTerm_edge = np.around(latTerm_edge, 2)

    nlonTerm = len(lonTerm)
    nlatTerm = len(latTerm)

    termAreas = np.zeros((nlatTerm, nlonTerm))
    # take advantage of  regular grid to compute areas equal for each gridbox at same latitude
    for iy in range(nlatTerm):
        termAreas[iy, :] = (
            area_of_rectangle_m2(
                latTerm_edge[iy], latTerm_edge[iy + 1], lonTerm_edge[0], lonTerm_edge[-1]
            )
            / lonTerm.size
        )
    # now collect some domain information
    domain_ds = config.domain_dataset()

    LATD = domain_ds["LATD"][:].values.squeeze()
    LOND = domain_ds["LOND"].values.squeeze()
    LAT = domain_ds.variables["LAT"].values.squeeze()
    cmaqArea = domain_ds.XCELL * domain_ds.YCELL

    indxPath = config.as_intermediate_file("TERM_ind_x.p.gz")
    indyPath = config.as_intermediate_file("TERM_ind_y.p.gz")
    coefsPath = config.as_intermediate_file("TERM_ind_coefs.p.gz")

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

            ixminl = bisect.bisect_right(lonTerm_edge, xmin)
            ixmaxr = bisect.bisect_right(lonTerm_edge, xmax)
            iyminl = bisect.bisect_right(latTerm_edge, ymin)
            iymaxr = bisect.bisect_right(latTerm_edge, ymax)

            for ix, iy in itertools.product(
                range(max(0, ixminl - 1), min(nlonTerm, ixmaxr)),
                range(max(0, iyminl - 1), min(nlatTerm, iymaxr)),
            ):
                Term_gridcell = geometry.box(
                    lonTerm_edge[ix], latTerm_edge[iy], lonTerm_edge[ix + 1], latTerm_edge[iy + 1]
                )
                if CMAQ_gridcell.intersects(Term_gridcell):
                    intersection = CMAQ_gridcell.intersection(Term_gridcell)
                    (intersection.area / CMAQ_gridcell.area)  ## fraction of CMAQ cell covered
                    weight2 = (
                        intersection.area / Term_gridcell.area
                    )  ## fraction of TERM cell covered
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

    subset = ncin["ch4_emissions_2010_2016.asc"][...]  # is masked array
    subset = subset.data  # grab value
    np.clip(
        subset, 0.0, None, out=subset
    )  # negative are missing values so remove by clipping in place
    subset = subset[-1::-1, :]  # reverse latitudes
    subset *= 1e9 / termAreas  # converting from mtCH4/gridcell to kg/m^2
    cmaqAreas = np.ones(LAT.shape) * cmaqArea  # all grid cells equal area
    resultNd = redistribute_spatially(LAT.shape, ind_x, ind_y, coefs, subset, termAreas, cmaqAreas)
    resultNd /= SECS_PER_YEAR
    ncin.close()

    write_layer(config.output_domain_file,
                "OCH4_TERMITE",
                resultNd,
                config = config,
                )
    return np.array(resultNd)


if __name__ == "__main__":
    config = load_config_from_env()
    processEmissions(config)
    sum_layers(config.output_domain_file)
