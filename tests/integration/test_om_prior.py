from testing import dataset_metrics


def test_009_prior_emissions_ds(prior_emissions_ds):
    assert dataset_metrics(prior_emissions_ds) == {
        'max': {
            'LANDMASK': 1.0,
            'OCH4_TOTAL': 8.105908627681788e-09,
            'ch4_sector_agriculture': 1.3196047170278112e-12,
            'ch4_sector_coal': 8.072982591959399e-09,
            'ch4_sector_electricity': 1.2683449229281463e-11,
            'ch4_sector_fire': 5.498670963000052e-11,
            'ch4_sector_industrial': 5.351265777744653e-13,
            'ch4_sector_livestock': 7.545056510007907e-11,
            'ch4_sector_lulucf': 1.4454168861914367e-10,
            'ch4_sector_oil_gas': 5.6714881375567926e-11,
            'ch4_sector_stationary': 1.3362230506306242e-11,
            'ch4_sector_termite': 3.38580183854853e-12,
            'ch4_sector_transport': 1.28013009489856e-12,
            'ch4_sector_waste': 2.817024580114932e-12,
            'ch4_sector_wetlands': 9.336642787030613e-13,
            'ch4_total': 8.105908627681788e-09,
            'lambert_conformal': 0,
            'land_mask': 1,
            'lat': -22.806066513061523,
            'lon': 149.1439208984375,
            'x_bounds': 1580000.375,
            'y_bounds': 414369.5,
        },
        'mean': {
            'LANDMASK': 1.0,
            'OCH4_TOTAL': 4.527375484529345e-10,
            'ch4_sector_agriculture': 1.0532989458203914e-12,
            'ch4_sector_coal': 3.979529404503474e-10,
            'ch4_sector_electricity': 2.2548354185389268e-13,
            'ch4_sector_fire': 3.6974516872713414e-13,
            'ch4_sector_industrial': 5.344609974538503e-14,
            'ch4_sector_livestock': 4.0547154335803873e-11,
            'ch4_sector_lulucf': 7.935998439039457e-12,
            'ch4_sector_oil_gas': 5.671488137556792e-13,
            'ch4_sector_stationary': 1.3345610816621784e-12,
            'ch4_sector_termite': 2.436579367090519e-12,
            'ch4_sector_transport': 1.27853789328799e-13,
            'ch4_sector_waste': 4.6656960187772004e-14,
            'ch4_sector_wetlands': 8.66815276056264e-14,
            'ch4_total': 4.527375484529345e-10,
            'lambert_conformal': 0.0,
            'land_mask': 1.0,
            'lat': -23.267749786376953,
            'lon': 148.6399383544922,
            'x_bounds': 1530000.375,
            'y_bounds': 364369.5,
        },
        'x_band': {
            'LANDMASK': 10.0,
            'OCH4_TOTAL': 3.881333541002702e-09,
            'ch4_sector_agriculture': 2.4194872992444853e-11,
            'ch4_sector_coal': 2.8558975726436694e-09,
            'ch4_sector_electricity': 0.0,
            'ch4_sector_fire': 0.0,
            'ch4_sector_industrial': 9.990360612431248e-13,
            'ch4_sector_livestock': 8.812359129868445e-10,
            'ch4_sector_lulucf': 4.318257917252425e-11,
            'ch4_sector_oil_gas': 0.0,
            'ch4_sector_stationary': 2.494615421637521e-11,
            'ch4_sector_termite': 4.7307820855158056e-11,
            'ch4_sector_transport': 2.389894617466093e-12,
            'ch4_sector_waste': 0.0,
            'ch4_sector_wetlands': 1.1796965896142583e-12,
            'ch4_total': 3.881333541002702e-09,
            'land_mask': 10,
            'lat': -232.6233367919922,
            'lon': 1486.8963623046875,
        },
        'y_band': {
            'LANDMASK': 10.0,
            'OCH4_TOTAL': 1.723023891570012e-08,
            'ch4_sector_agriculture': 2.3428548325447984e-11,
            'ch4_sector_coal': 1.6145965183918798e-08,
            'ch4_sector_electricity': 0.0,
            'ch4_sector_fire': 0.0,
            'ch4_sector_industrial': 3.7006265826194363e-13,
            'ch4_sector_livestock': 1.0031707194660715e-09,
            'ch4_sector_lulucf': 0.0,
            'ch4_sector_oil_gas': 0.0,
            'ch4_sector_stationary': 9.240547464560038e-12,
            'ch4_sector_termite': 4.639714307197451e-11,
            'ch4_sector_transport': 8.852640954771137e-13,
            'ch4_sector_waste': 0.0,
            'ch4_sector_wetlands': 7.814475668897097e-13,
            'ch4_total': 1.723023891570012e-08,
            'land_mask': 10,
            'lat': -232.2213897705078,
            'lon': 1486.336669921875,
        },
    }


def test_011_output_dims(prior_emissions_ds):
    expected_dimensions = {
        "time": 2,
        "vertical": 1,
        "y": 10,
        "x": 10,
        "cell_bounds": 2,
        "time_period": 2,
    }

    assert prior_emissions_ds.sizes == expected_dimensions


def test_012_output_variable_attributes(prior_emissions_ds):
    assert prior_emissions_ds.variables["ch4_total"].attrs == {
        "units": "kg/m2/s",
        "standard_name": "surface_upward_mass_flux_of_methane",
        "long_name": "total expected flux of methane based on public data",
        "grid_mapping": "lambert_conformal",
    }

    for layer_name in [layer for layer in list(prior_emissions_ds.variables.keys()) if layer.startswith("ch4_sector_")]:
        assert prior_emissions_ds.variables[layer_name].attrs["units"] == "kg/m2/s"
        assert prior_emissions_ds.variables[layer_name].attrs["long_name"] == f"expected flux of methane caused by sector: {layer_name.replace('ch4_sector_', '')}"
        assert prior_emissions_ds.variables[layer_name].attrs["standard_name"].startswith("surface_upward_mass_flux_of_methane_due_to_emission_from_")
        assert prior_emissions_ds.variables[layer_name].attrs["grid_mapping"] == "lambert_conformal"

    # TODO: remove when OCH4_TOTAL layer is removed
    assert prior_emissions_ds.variables["OCH4_TOTAL"].attrs["deprecated"] == "This variable is deprecated and will be removed in future versions"
    assert prior_emissions_ds.variables["OCH4_TOTAL"].attrs["superseded_by"] == "ch4_total"
