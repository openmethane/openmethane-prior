import datetime
import pytest

from openmethane_prior.inventory.data import inventory_data_source
from openmethane_prior.inventory.inventory import get_sector_emissions_by_code
from openmethane_prior.layers.omIndustrialStationaryTransportEmis import sector_meta_map as ntlt_sector_meta
from openmethane_prior.layers.omAgLulucfWasteEmis import sector_meta_map as landuse_sector_meta
from openmethane_prior.layers.omElectricityEmis import sector_meta as electricity_sector_meta
from openmethane_prior.layers.omFugitiveEmis import sector_meta as fugitive_sector_meta


@pytest.fixture()
def emissions_inventory(input_files, data_manager):
    return data_manager.get_asset(inventory_data_source).data

@pytest.fixture()
def all_sector_meta():
    all_inventory_sectors = [
        fugitive_sector_meta,
        electricity_sector_meta,
        *ntlt_sector_meta.values(),
        *landuse_sector_meta.values(),
    ]
    all_sectors = {}
    for sector_meta in all_inventory_sectors:
        all_sectors[sector_meta.name] = sector_meta
    return all_sectors


def test_inventory_get_sector_emissions_by_code(all_sector_meta, emissions_inventory):
    expected_annual_emissions = {
        "agriculture": 270672674.52687985,
        "electricity": 11162651.14214232,
        "fugitive": 1164824228.295256,
        "industrial": 2937681.1201194106,
        "lulucf": 642498499.5484172,
        "stationary": 48906820.467345454,
        "transport": 11525390.64124776,
        "waste": 478278828.9647396,
    }

    annual_emissions = {}
    for name in expected_annual_emissions.keys():
        annual_emissions[name] = get_sector_emissions_by_code(
            emissions_inventory=emissions_inventory,
            start_date=datetime.date(2023, 1, 1),
            end_date=datetime.date(2023, 12, 31),
            category_codes=all_sector_meta[name].unfccc_categories,
        )

    assert annual_emissions == expected_annual_emissions

    monthly_fugitive_emissions = get_sector_emissions_by_code(
        emissions_inventory=emissions_inventory,
        start_date=datetime.date(2023, 1, 1),
        end_date=datetime.date(2023, 1, 31),
        category_codes=all_sector_meta["fugitive"].unfccc_categories,
    )

    # emissions for a shorter period should be scaled from the annual emissions
    assert monthly_fugitive_emissions == expected_annual_emissions["fugitive"] * (31 / 365)
