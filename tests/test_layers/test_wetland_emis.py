import netCDF4 as nc
import numpy as np

from openmethane_prior.layers.omWetlandEmis import make_wetland_climatology
from openmethane_prior.utils import area_of_rectangle_m2


def test_wetland_emis(config, input_files):
    # TODO: convert into an actual test
    """Test totals for WETLAND emissions between original and remapped"""
    remapped = make_wetland_climatology(config=config, forceUpdate=True)
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

    areas = np.zeros((nlatWetland, nlonWetland))
    # take advantage of  regular grid to compute areas equal for each gridbox at same latitude
    for iy in range(nlatWetland):
        areas[iy, :] = (
            area_of_rectangle_m2(
                latWetland_edge[iy],
                latWetland_edge[iy + 1],
                lonWetland_edge[0],
                lonWetland_edge[-1],
            )
            / lonWetland.size
        )
    domain_ds = config.domain_dataset()
    LATD = domain_ds.variables["LATD"].values.squeeze()
    LOND = domain_ds.variables["LOND"].values.squeeze()
    indLat = (latWetland > LATD.min()) & (latWetland < LATD.max())
    indLon = (lonWetland > LOND.min()) & (lonWetland < LOND.max())
    flux = ncin["totflux"][...]
    # make climatology
    climatology = np.zeros(
        (12, flux.shape[1], flux.shape[2])
    )  # same spatial domain but monthly climatology
    for month in range(12):
        climatology[month, ...] = flux[month::12, ...].mean(
            axis=0
        )  # average over time axis with stride 12

    inds = np.ix_(indLat, indLon)
    wetlandTotals = [(areas * climatology[month])[inds].sum() for month in range(12)]
    area = domain_ds.XCELL * domain_ds.YCELL
    remappedTotals = [
        remapped[month, ...].sum() * area for month in range(12)
    ]  # conversion from kg to mt
    print(list(zip(wetlandTotals, remappedTotals)))
