import datetime
import pytest

from openmethane_prior.data_sources.inventory.data import inventory_data_source
from openmethane_prior.data_sources.inventory.inventory import get_sector_emissions_by_code
from openmethane_prior.sectors import all_sectors


@pytest.fixture()
def inventory_df(input_files, data_manager):
    return data_manager.get_asset(inventory_data_source).data

@pytest.fixture()
def all_sector_meta():
    inventory_sectors = [s for s in all_sectors if s.unfccc_categories is not None]

    all_sectors_map = {}
    for sector_meta in inventory_sectors:
        all_sectors_map[sector_meta.name] = sector_meta
    return all_sectors_map


def test_inventory_get_sector_emissions_by_code(all_sector_meta, inventory_df):
    expected_annual_emissions = {
        "agriculture": 153367168.6905247,
        "coal": 901455051.0124934,
        "electricity": 11164637.314332796,
        "industrial": 2937681.1201194106,
        "lulucf": 661762727.6374531,
        "oil_gas": 238171271.587112,
        "stationary": 73354555.56013045,
        "transport": 11702390.307919662,
        "waste": 481160233.5451011,
    }

    annual_emissions = {}
    for name in expected_annual_emissions.keys():
        annual_emissions[name] = get_sector_emissions_by_code(
            emissions_inventory=inventory_df,
            start_date=datetime.date(2022, 7, 1),
            end_date=datetime.date(2023, 6, 30),
            category_codes=all_sector_meta[name].unfccc_categories,
        )

    assert annual_emissions == pytest.approx(expected_annual_emissions)

    monthly_coal_emissions = get_sector_emissions_by_code(
        emissions_inventory=inventory_df,
        start_date=datetime.date(2023, 1, 1),
        end_date=datetime.date(2023, 1, 31),
        category_codes=all_sector_meta["coal"].unfccc_categories,
    )

    # emissions for a shorter period should be scaled from the annual emissions
    assert monthly_coal_emissions == pytest.approx(expected_annual_emissions["coal"] * (31 / 365))
