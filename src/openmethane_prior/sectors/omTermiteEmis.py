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
from openmethane_prior.lib.data_manager.manager import DataManager
from openmethane_prior.lib.data_manager.source import DataSource
from shapely import geometry
import xarray as xr

from openmethane_prior.lib.config import load_config_from_env, parse_cli_to_env
from openmethane_prior.lib.outputs import add_ch4_total, add_sector, create_output_dataset, write_output_dataset
from openmethane_prior.lib.sector.config import PriorSectorConfig
from openmethane_prior.lib.sector.sector import SectorMeta
from openmethane_prior.lib.utils import (
    SECS_PER_YEAR,
    area_of_rectangle_m2,
    load_zipped_pickle,
    redistribute_spatially,
    save_zipped_pickle,
)

sector_meta = SectorMeta(
    name="termite",
    emission_category="natural",
    cf_standard_name="termites",
)

termites_data_source = DataSource(
    name="termites",
    url="https://openmethane.s3.amazonaws.com/prior/inputs/termite_emissions_2010-2016.nc",
)

def processEmissions(  # noqa: PLR0915
    sector_config: PriorSectorConfig,
    prior_ds: xr.Dataset,
    forceUpdate: bool = False,
):
    """Remap termite emissions to the CMAQ domain"""
    config = sector_config.prior_config

    termites_asset = sector_config.data_manager.get_asset(termites_data_source)
    ncin = nc.Dataset(termites_asset.path, "r")
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
    domain_grid = config.domain_grid()

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
    cmaq_areas = np.ones(domain_grid.shape) * domain_grid.cell_area  # all grid cells equal area
    resultNd = redistribute_spatially(domain_grid.shape, ind_x, ind_y, coefs, subset, termAreas, cmaq_areas)
    resultNd /= SECS_PER_YEAR
    ncin.close()

    add_sector(
        prior_ds=prior_ds,
        sector_data=resultNd,
        sector_meta=sector_meta,
        # source dataset is a coarse grid, cells over water should be
        # excluded from results because there won't be termites there!
        apply_landmask=True,
    )
    return resultNd


if __name__ == "__main__":
    parse_cli_to_env()
    config = load_config_from_env()
    data_manager = DataManager(data_path=config.input_path, prior_config=config)
    sector_config = PriorSectorConfig(prior_config=config, data_manager=data_manager)

    ds = create_output_dataset(config)
    processEmissions(sector_config, ds)
    add_ch4_total(ds)
    write_output_dataset(config, ds)
