import datetime
import pytest

from openmethane_prior.lib import create_prior, PriorConfig
from openmethane_prior.sectors.waste import sector

@pytest.fixture()
def waste_config_params(cache_dir, config_params, tmp_path):
    data_dir = tmp_path / "waste_test"
    return dict(
        domain_path=config_params["domain_path"],
        input_path=data_dir / "inputs",
        intermediates_path=data_dir / "intermediates",
        output_path=data_dir / "outputs",
        input_cache=cache_dir,
    )


def test_sector_waste_pre_sgm(input_files, waste_config_params):
    """Run the full waste sector over the au-test domain."""
    config = PriorConfig(
        **waste_config_params,
        start_date=datetime.datetime(2022, 7, 1, 0, 0),
        end_date=datetime.datetime(2022, 7, 31, 0, 0),
    )
    config.prepare_paths()
    config.load_cached_inputs()

    # run the prior and return the result
    prior_waste_ds = create_prior(config, [sector])

    assert prior_waste_ds['ch4_sector_waste'].max().item() == 3.546416257544296e-12
    assert prior_waste_ds['ch4_sector_waste'].mean().item() == 5.87375074492232e-14


def test_waste_sector_post_sgm(input_files, waste_config_params):
    """Run the full oil and gas sector over the au-test domain, for a period
    where per-facility methane emissions are being published in the Safeguard
    Mechanism."""
    config = PriorConfig(
        **waste_config_params,
        start_date=datetime.datetime(2023, 7, 1, 0, 0),
        end_date=datetime.datetime(2023, 7, 31, 0, 0),
    )
    config.prepare_paths()
    config.load_cached_inputs()

    # run the prior and return the result
    prior_waste_ds = create_prior(config, [sector])

    # config.cache_inputs()

    assert prior_waste_ds['ch4_sector_waste'].max().item() == 3.578191860460334e-12
    assert prior_waste_ds['ch4_sector_waste'].mean().item() == 5.926379102441715e-14
