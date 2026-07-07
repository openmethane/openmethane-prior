import datetime
import pytest

from openmethane_prior.lib import PriorConfig, create_prior
from openmethane_prior.sectors.oil_gas import sector


@pytest.fixture()
def oil_gas_config_params(cache_dir, config_params, tmp_path):
    data_dir = tmp_path / "oil_gas_test"
    return dict(
        domain_path=config_params["domain_path"],
        input_path=data_dir / "inputs",
        intermediates_path=data_dir / "intermediates",
        output_path=data_dir / "outputs",
        input_cache=cache_dir,
    )


def test_oil_gas_sector_pre_sgm(input_files, oil_gas_config_params, start_date, end_date):
    """Run the full oil and gas sector over the au-test domain, for a period
    prior to per-facility methane emissions being published in the Safeguard
    Mechanism."""
    config = PriorConfig(
        **oil_gas_config_params,
        start_date=start_date,
        end_date=end_date,
    )
    config.prepare_paths()
    config.load_cached_inputs()

    # run the prior and return the result
    prior_oil_gas_ds = create_prior(config, [sector])

    # config.cache_inputs()

    assert prior_oil_gas_ds['ch4_total'].max().item() == 5.6714881375567926e-11
    assert prior_oil_gas_ds['ch4_sector_oil_gas'].max().item() == 5.6714881375567926e-11

    assert prior_oil_gas_ds['ch4_total'].mean().item() == 5.671488137556792e-13
    assert prior_oil_gas_ds['ch4_sector_oil_gas'].mean().item() == 5.671488137556792e-13


def test_oil_gas_sector_post_sgm(input_files, oil_gas_config_params):
    """Run the full oil and gas sector over the au-test domain, for a period
    where per-facility methane emissions are being published in the Safeguard
    Mechanism."""
    start_date = datetime.datetime(2023, 7, 1, 0, 0)
    end_date = datetime.datetime(2024, 6, 30, 0, 0)
    config = PriorConfig(
        **oil_gas_config_params,
        start_date=start_date,
        end_date=end_date,
    )
    config.prepare_paths()
    config.load_cached_inputs()

    # run the prior and return the result
    prior_oil_gas_ds = create_prior(config, [sector])

    # config.cache_inputs()

    assert prior_oil_gas_ds['ch4_total'].max().item() == 5.981512482274273e-11
    assert prior_oil_gas_ds['ch4_sector_oil_gas'].max().item() == 5.981512482274273e-11

    assert prior_oil_gas_ds['ch4_total'].mean().item() == 5.981512482274273e-13
    assert prior_oil_gas_ds['ch4_sector_oil_gas'].mean().item() == 5.981512482274273e-13
