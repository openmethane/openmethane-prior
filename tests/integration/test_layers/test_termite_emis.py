import netCDF4 as nc
import numpy as np
import pytest

from openmethane_prior.lib.outputs import create_output_dataset
from openmethane_prior.sectors.termite.sector import sector as termites_sector, termites_data_source
from openmethane_prior.lib.sector.config import PriorSectorConfig
from openmethane_prior.lib.utils import area_of_rectangle_m2

@pytest.mark.skip(reason="Makes no assertions")
def test_termite_emis(config, input_files, data_manager):
    # TODO: Check the output correctly
    prior_ds = create_output_dataset(config)
    sector_config = PriorSectorConfig(prior_config=config, data_manager=data_manager)

    remapped = termites_sector.create_estimate(termites_sector, sector_config, prior_ds)

    termites_asset = data_manager.get_asset(termites_data_source)
    ncin = nc.Dataset(termites_asset.path, "r")

    latTerm = np.around(np.float64(ncin.variables["lat"][:]), 3)
    latTerm = latTerm[-1::-1]  # reversing order, we need south first
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

    areas = np.zeros((nlatTerm, nlonTerm))
    # take advantage of  regular grid to compute areas equal for each gridbox at same latitude
    for iy in range(nlatTerm):
        areas[iy, :] = (
            area_of_rectangle_m2(
                latTerm_edge[iy], latTerm_edge[iy + 1], lonTerm_edge[0], lonTerm_edge[-1]
            )
            / lonTerm.size
        )

    domain_ds = config.domain_dataset()
    LATD = domain_ds.variables["LATD"].values.squeeze()
    LOND = domain_ds.variables["LOND"].values.squeeze()
    indLat = (latTerm > LATD.min()) & (latTerm < LATD.max())
    indLon = (lonTerm > LOND.min()) & (lonTerm < LOND.max())
    TermCH4 = ncin["ch4_emissions_2010_2016.asc"][...][-1::-1, :]  # reverse latitudes
    #    np.clip( TermCH4, 0., None, out=TermCH4) # remove negative values in place
    inds = np.ix_(indLat, indLon)
    TermTotals = TermCH4[inds].sum()
    area = domain_ds.XCELL * domain_ds.YCELL
    remappedTotals = remapped.sum() * area / 1e9  # conversion from kg to mt
    print(TermTotals, remappedTotals)
