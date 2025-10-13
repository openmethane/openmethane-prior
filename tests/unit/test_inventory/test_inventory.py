import datetime
import pytest

from openmethane_prior.inventory.inventory import create_emissions_inventory, get_sector_emissions_by_code
from openmethane_prior.inventory.unfccc import create_category_list

@pytest.fixture()
def category_list():
    return create_category_list([
        ["1", "Energy", "", "", ""],
        ["1.A.1", "Energy", "Fuel Combustion", "Other", ""],
        ["1.A.1.a", "Energy", "Fuel Combustion", "Other", "Mobile"],
        ["1.A", "Energy", "Fuel Combustion", "", ""],
        ["1.B", "Energy", "Fugitive Emissions From Fuels", "", ""],
        ["2", "Industrial Processes", "", "", ""],
    ])

def test_inventory_create_emissions_inventory(category_list):
    inventory = create_emissions_inventory(
        categories=category_list,
        inventory_list=[
            ["1993", "Energy", "Fuel Combustion", "Other", "Mobile", "", "1.1"],
            ["1994", "Energy", "Fuel Combustion", "Other", "Mobile", "", "2.2"],
            ["1995", "Energy", "Fuel Combustion", "Other", "Mobile", "", "3.3"],
            ["1993", "Energy", "Fugitive Emissions From Fuels", "Smoke", "Smoke from AI fires", "", "0.2"],
            ["1994", "Energy", "Fugitive Emissions From Fuels", "Smoke", "Smoke from AI fires", "", "0.5"],
            ["1995", "Energy", "Fugitive Emissions From Fuels", "Smoke", "Smoke from AI fires", "", "0.8"],
        ],
    )

    assert len(inventory) == 2 # 2 unique categories
    assert inventory[0].unfccc_category.code == "1.A.1.a" # exact match
    assert inventory[0].ch4_emissions == {
        1993: 1.1 * 1e6,
        1994: 2.2 * 1e6,
        1995: 3.3 * 1e6,
    }
    assert inventory[1].unfccc_category.code == "1.B" # nearest match
    assert inventory[1].ch4_emissions == {
        1993: 0.2 * 1e6,
        1994: 0.5 * 1e6,
        1995: 0.8 * 1e6,
    }


def test_inventory_get_sector_emissions_by_code(category_list):
    inventory = create_emissions_inventory(
        categories=category_list,
        inventory_list=[
            ["1993", "Energy", "Fuel Combustion", "Other", "Mobile", "", "1.1"],
            ["1994", "Energy", "Fuel Combustion", "Other", "Mobile", "", "2.2"],
            ["1995", "Energy", "Fuel Combustion", "Other", "Mobile", "", "3.3"],
            ["1993", "Energy", "Fugitive Emissions From Fuels", "Smoke", "Smoke from AI fires", "", "0.2"],
            ["1994", "Energy", "Fugitive Emissions From Fuels", "Smoke", "Smoke from AI fires", "", "0.5"],
            ["1995", "Energy", "Fugitive Emissions From Fuels", "Smoke", "Smoke from AI fires", "", "0.8"],
            ["1993", "Industrial Processes", "Building stuff", "", "", "", "0.7"],
            ["1994", "Industrial Processes", "Building stuff", "", "", "", "0.11"],
            ["1995", "Industrial Processes", "Building stuff", "", "", "", "0.13"],
        ],
    )

    energy_emissions = get_sector_emissions_by_code(
        emissions_inventory=inventory,
        category_codes=["1"],
        start_date=datetime.date(1993, 1, 1),
        end_date=datetime.date(1993, 1, 31),
    )

    # search finds both categories, and takes the fraction of the year
    assert energy_emissions == (1.1 + 0.2) * (31 / 365) * 1e6

    multi_emissions = get_sector_emissions_by_code(
        emissions_inventory=inventory,
        category_codes=["1.A", "2"], # multiple codes
        start_date=datetime.date(1993, 1, 1),
        end_date=datetime.date(1993, 1, 31),
    )

    # search finds both categories, and takes the fraction of the year
    assert multi_emissions == (1.1 + 0.7) * (31 / 365) * 1e6

    future_emissions = get_sector_emissions_by_code(
        emissions_inventory=inventory,
        category_codes=["1.A", "2"], # multiple codes
        start_date=datetime.date(1997, 1, 1),
        end_date=datetime.date(1997, 1, 31),
    )

    # search finds no emissions for 1997, uses last available year 1995
    assert future_emissions == (3.3 + 0.13) * (31 / 365) * 1e6

    past_emissions = get_sector_emissions_by_code(
        emissions_inventory=inventory,
        category_codes=["1.A", "2"], # multiple codes
        start_date=datetime.date(1990, 1, 1),
        end_date=datetime.date(1990, 1, 31),
    )

    # search finds no emissions for 1990, uses first available year 1993
    assert multi_emissions == (1.1 + 0.7) * (31 / 365) * 1e6

