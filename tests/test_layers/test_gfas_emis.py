import datetime

import netCDF4 as nc
import numpy as np
import pytest

from openmethane_prior.layers.omGFASEmis import processEmissions
from openmethane_prior.omInputs import domainXr
from openmethane_prior.omUtils import area_of_rectangle_m2


@pytest.mark.skip(reason="Needs fixtures reshuffled")
def test_gfas_emis():  # test totals for GFAS emissions between original and remapped
    remapped = processEmissions(
        datetime.date(2022, 7, 2), datetime.date(2022, 7, 2), forceUpdate=True
    )
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
            area_of_rectangle_m2(
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