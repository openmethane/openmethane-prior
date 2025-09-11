
from openmethane_prior.units import kg_to_kg_m2_s, kg_to_period_cell_flux


def test_units_kg_to_kg_m2_s():
    assert kg_to_kg_m2_s(60000, 1000, 20) == 3.0
    assert kg_to_kg_m2_s(60000, 100, 20) == 30.0
    assert kg_to_kg_m2_s(60000, 1000, 30) == 2.0
    assert kg_to_kg_m2_s(60000, 100000000.0, 2 *  24 * 60 * 60) == 3.4722222222222217e-09

def test_units_kg_to_period_cell_flux(config, input_files):
    # inputs to kg_to_period_cell_flux
    assert config.domain_grid().cell_area == 100000000.0
    assert (config.end_date - config.start_date).days + 1 == 2

    assert kg_to_period_cell_flux(60000, config) == 3.4722222222222217e-09

