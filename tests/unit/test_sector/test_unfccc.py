
from openmethane_prior.sector.unfccc import Category, create_category_list, find_category_by_name, \
    is_code_in_code_family


def test_unfccc_create_category_list():
    category_list = create_category_list([
        ["1", "Energy", "", "", ""],
        ["1.A.1", "Energy", "Fuel Combustion", "Other", ""],
        ["1.A.1.a", "Energy", "Fuel Combustion", "Other", "Mobile"],
        ["1.A", "Energy", "Fuel Combustion", "", ""],
        ["1.B", "Energy", "Fugitive Emissions From Fuels", "", ""],
        ["2", "Industrial Processes", "", "", ""],
    ])

    assert category_list == [
        Category(code="1", api_level_names=["Energy", "", "", ""]),
        Category(code="1.A.1", api_level_names=["Energy", "Fuel Combustion", "Other", ""]),
        Category(code="1.A.1.a", api_level_names=["Energy", "Fuel Combustion", "Other", "Mobile"]),
        Category(code="1.A", api_level_names=["Energy", "Fuel Combustion", "", ""]),
        Category(code="1.B", api_level_names=["Energy", "Fugitive Emissions From Fuels", "", ""]),
        Category(code="2", api_level_names=["Industrial Processes", "", "", ""]),
    ]

def test_unfccc_find_category_by_name():
    category_list = [
        Category(code="1", api_level_names=["Energy", "", "", ""]),
        Category(code="1.A.1", api_level_names=["Energy", "Fuel Combustion", "Other", ""]),
        Category(code="1.A.1.a", api_level_names=["Energy", "Fuel Combustion", "Other", "Mobile"]),
        # list can be out of order
        Category(code="1.A", api_level_names=["Energy", "Fuel Combustion", "", ""]),
        Category(code="1.B", api_level_names=["Energy", "Fugitive Emissions From Fuels", "", ""]),
        Category(code="2", api_level_names=["Industrial Processes", "", "", ""]),
    ]

    # no match returns None
    assert find_category_by_name(category_list, ["Not found", "", "", ""]) is None

    # exact matches
    assert find_category_by_name(category_list, ["Energy", "", "", ""]).code == "1"
    assert find_category_by_name(category_list, ["Industrial Processes", "", "", ""]).code == "2"
    assert find_category_by_name(category_list, ["Energy", "Fuel Combustion", "", ""]).code == "1.A"
    assert find_category_by_name(category_list, ["Energy", "Fugitive Emissions From Fuels", "", ""]).code == "1.B"

    # partial matches
    assert find_category_by_name(category_list, ["Energy", "N/A", "", ""]).code == "1"
    assert find_category_by_name(category_list, ["Energy", "Fuel Combustion", "N/A", ""]).code == "1.A"
    assert find_category_by_name(category_list, ["Industrial Processes", "N/A", "", ""]).code == "2"


def test_unfccc_is_code_in_code_family():
    test_family = ["1.A.1.b", "1.A.1.c", "1.A.2", "1.A.4", "1.A.5", "1.C"]

    assert is_code_in_code_family("1.A.1.b", test_family)
    assert is_code_in_code_family("1.A.2.a", test_family)
    assert is_code_in_code_family("1.C", test_family)
    assert is_code_in_code_family("1.C.1", test_family)

    assert not is_code_in_code_family("1.A.1.a", test_family)
    assert not is_code_in_code_family("1.D", test_family)
    assert not is_code_in_code_family("2", test_family)
