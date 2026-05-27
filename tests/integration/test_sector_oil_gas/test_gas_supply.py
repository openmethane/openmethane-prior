import numpy as np

from openmethane_prior.data_sources.au_shapes import au_shapes_states_data_source
from openmethane_prior.data_sources.nightlights import night_lights_data_source
from openmethane_prior.data_sources.safeguard import safeguard_mechanism_data_source
from openmethane_prior.lib import DataManager, PriorConfig
from openmethane_prior.sectors.oil_gas.safeguard import gas_supply_emissions


def test_gas_supply(input_files, config):
    # au-test has no overlap with gas supply areas, use full aust10km domain
    aust10km_config = PriorConfig(
        start_date=config.start_date,
        end_date=config.end_date,
        domain_path=config.inventory_domain_path, # aust10km
        inventory_domain_path=config.inventory_domain_path,
        input_path=config.input_path,
        intermediates_path=config.intermediates_path,
        output_path=config.output_path,
        input_cache=config.input_cache,
    )
    data_manager = DataManager(
        prior_config=aust10km_config,
        data_path=aust10km_config.input_path,
    )

    au_states_df = data_manager.get_asset(au_shapes_states_data_source).data
    nightlights_da = data_manager.get_asset(night_lights_data_source)
    safeguard_facilities_df = data_manager.get_asset(safeguard_mechanism_data_source).data
    gas_supply_facilities_mask = safeguard_facilities_df["anzsic_code"].str.startswith("27") \
                                 & safeguard_facilities_df["state"].isin(au_states_df["short_name"])
    gas_supply_facilities_df = safeguard_facilities_df[gas_supply_facilities_mask]

    result = gas_supply_emissions(
        domain_grid=aust10km_config.domain_grid(),
        au_states=au_states_df,
        nightlights=nightlights_da.data,
        facilities_df=gas_supply_facilities_df,
    )

    np.testing.assert_approx_equal(result.sum(), gas_supply_facilities_df["ch4_kg"].sum())