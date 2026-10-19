from datetime import date
from openmethane_prior.lib.units import kg_to_kg_m2_s, kg_to_period_cell_flux, seconds_in_period, days_in_period, days_in_overlap


def test_units_days_in_period():
    assert days_in_period(date(2022, 12, 7), date(2022, 12, 7)) == 1
    assert days_in_period(date(2022, 12, 7), date(2022, 12, 8)) == 2
    assert days_in_period(date(2022, 12, 1), date(2022, 12, 31)) == 31
    assert days_in_period(date(2022, 1, 1), date(2022, 12, 31)) == 365

    # leap year
    assert days_in_period(date(2020, 2, 28), date(2020, 3, 1)) == 3
    # non-leap year
    assert days_in_period(date(2021, 2, 28), date(2021, 3, 1)) == 2

def test_units_days_in_overlap_unbounded_window():
    assert days_in_overlap(date(2023, 7, 1), date(2024, 6, 30), None, None) == 366


def test_units_days_in_overlap_partial_window():
    # window ends partway through the period
    assert days_in_overlap(date(2023, 7, 1), date(2024, 6, 30), None, date(2023, 11, 11)) == 134
    # window starts partway through the period
    assert days_in_overlap(date(2023, 7, 1), date(2024, 6, 30), date(2024, 6, 1), None) == 30
    # window contained within the period
    assert days_in_overlap(date(2023, 7, 1), date(2024, 6, 30), date(2023, 7, 10), date(2023, 7, 19)) == 10
    # period contained within the window
    assert days_in_overlap(date(2023, 10, 1), date(2023, 10, 30), date(2006, 1, 1), date(2023, 11, 11)) == 30
    # overlapping by a single day
    assert days_in_overlap(date(2023, 11, 11), date(2023, 11, 30), None, date(2023, 11, 11)) == 1


def test_units_days_in_overlap_no_overlap():
    assert days_in_overlap(date(2023, 12, 1), date(2023, 12, 31), None, date(2023, 11, 11)) == 0
    assert days_in_overlap(date(2023, 12, 1), date(2023, 12, 31), date(2024, 1, 1), None) == 0
    assert days_in_overlap(date(2023, 12, 1), date(2023, 12, 31), date(2020, 1, 1), date(2020, 12, 31)) == 0


def test_units_seconds_in_period():
    seconds_in_day = 24 * 60 * 60

    assert seconds_in_period(date(2022, 12, 7), date(2022, 12, 7)) == seconds_in_day
    assert seconds_in_period(date(2022, 12, 7), date(2022, 12, 8)) == seconds_in_day * 2
    assert seconds_in_period(date(2022, 12, 1), date(2022, 12, 31)) == seconds_in_day * 31
    assert seconds_in_period(date(2022, 1, 1), date(2022, 12, 31)) == seconds_in_day * 365

    # leap year
    assert seconds_in_period(date(2020, 2, 28), date(2020, 3, 1)) == seconds_in_day * 3
    # non-leap year
    assert seconds_in_period(date(2021, 2, 28), date(2021, 3, 1)) == seconds_in_day * 2

def test_units_kg_to_kg_m2_s():
    assert kg_to_kg_m2_s(60000, 1000, 20) == 3.0
    assert kg_to_kg_m2_s(60000, 100, 20) == 30.0
    assert kg_to_kg_m2_s(60000, 1000, 30) == 2.0
    assert kg_to_kg_m2_s(60000, 100000000.0, 2 *  24 * 60 * 60) == 3.4722222222222217e-09

def test_units_kg_to_period_cell_flux(config, input_files):
    # inputs to kg_to_period_cell_flux
    assert config.domain().grid.cell_area == 100000000.0
    assert (config.end_date - config.start_date).days + 1 == 2

    assert kg_to_period_cell_flux(60000, config) == 3.4722222222222217e-09

