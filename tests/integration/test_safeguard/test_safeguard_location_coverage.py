import datetime

import attrs
import pandas as pd
import pytest

from openmethane_prior.data_sources.safeguard import (
    safeguard_locations_data_source,
    safeguard_mechanism_data_source,
)
from openmethane_prior.data_sources.safeguard.data import (
    safeguard_locations_columns,
    safeguard_locations_year_columns,
    safeguard_tables,
)
from openmethane_prior.data_sources.safeguard.facility import filter_facilities
from openmethane_prior.data_sources.safeguard.location import filter_locations_for_financial_year
from openmethane_prior.lib import DataManager
from openmethane_prior.sectors.coal import sector as coal_sector
from openmethane_prior.sectors.oil_gas import sector as oil_gas_sector
from openmethane_prior.sectors.waste import sector as waste_sector


@pytest.mark.parametrize(
    "financial_year", sorted(safeguard_tables), ids=lambda financial_year: financial_year.label,
)
def test_safeguard_facilities_have_location_rows(config, financial_year):
    """Every Safeguard facility in a sector that places facilities at
    locations must have a row in the locations sheet for each financial year
    with a registered table, so a new year's table can't be added without its
    locations. A row with a blank data source id records a facility that is
    deliberately left unlocated.

    Fetches the live Safeguard table and locations sheet."""
    year_config = attrs.evolve(
        config,
        start_date=datetime.datetime.combine(financial_year.start, datetime.time()),
        end_date=datetime.datetime.combine(financial_year.start, datetime.time()),
    )
    data_manager = DataManager(prior_config=year_config, data_path=year_config.input_path)
    facilities_df = data_manager.get_asset(safeguard_mechanism_data_source).data
    locations_asset = data_manager.get_asset(safeguard_locations_data_source)

    # the parsed locations leave out rows with a blank id, so read every row
    # of the fetched sheets, limited to this financial year
    location_rows_df = pd.read_csv(locations_asset.path, dtype=str)
    location_rows_df = location_rows_df.rename(
        columns={**safeguard_locations_columns, **safeguard_locations_year_columns},
    )
    location_rows_df = filter_locations_for_financial_year(location_rows_df, financial_year)
    located_names = set(location_rows_df["safeguard_facility_name"])

    sector_codes = [
        *coal_sector.anzsic_codes, *oil_gas_sector.anzsic_codes, *waste_sector.anzsic_codes,
    ]
    sector_facilities_df = filter_facilities(facilities_df, anzsic_codes=sector_codes)
    # gas supply facilities are spread using nighttime lights, not locations
    gas_supply_mask = sector_facilities_df["anzsic_code"].str.startswith("27")
    sector_facilities_df = sector_facilities_df[~gas_supply_mask]

    unlocated = sorted(set(sector_facilities_df["facility_name"]) - located_names)

    assert len(sector_facilities_df) > 0
    assert unlocated == []
