import datetime

import attrs
import numpy as np

from openmethane_prior.data_sources.au_shapes import au_shapes_states_data_source
from openmethane_prior.data_sources.nightlights import night_lights_data_source
from openmethane_prior.data_sources.safeguard import safeguard_mechanism_data_source
from openmethane_prior.lib import DataManager, PriorConfig
from openmethane_prior.sectors.oil_gas.safeguard import gas_supply_emissions


def test_gas_supply(aust10km_config):
    # au-test has no overlap with gas supply areas, use full aust10km domain.
    # Safeguard data is read for the financial year of the configured period.
    config_2023 = attrs.evolve(
        aust10km_config,
        start_date=datetime.datetime(2023, 7, 1),
        end_date=datetime.datetime(2023, 7, 2),
    )
    data_manager = DataManager(
        prior_config=config_2023,
        data_path=config_2023.input_path,
    )

    au_states_df = data_manager.get_asset(au_shapes_states_data_source).data
    nightlights_da = data_manager.get_asset(night_lights_data_source)
    safeguard_facilities_df = data_manager.get_asset(safeguard_mechanism_data_source).data
    gas_supply_facilities_mask = safeguard_facilities_df["anzsic_code"].str.startswith("27") \
                                 & safeguard_facilities_df["state"].isin(au_states_df["short_name"])
    gas_supply_facilities_df = safeguard_facilities_df[gas_supply_facilities_mask]

    result = gas_supply_emissions(
        domain_grid=config_2023.domain().grid,
        au_states=au_states_df,
        nightlights=nightlights_da.data,
        facilities_df=gas_supply_facilities_df,
    )

    # gas supply facilities must be present for this test to be meaningful
    assert len(gas_supply_facilities_df) > 0
    np.testing.assert_approx_equal(result.sum(), gas_supply_facilities_df["ch4_kg"].sum())