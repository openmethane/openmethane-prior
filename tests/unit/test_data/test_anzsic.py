
from openmethane_prior.data_sources.safeguard.anzsic import simplify_anzsic_code, is_anzsic_code_in_code_family


def test_simplify_anzsic_code():
    # full codes
    assert simplify_anzsic_code("0111") == "0111"
    assert simplify_anzsic_code("1111") == "1111"
    assert simplify_anzsic_code("1123") == "1123"
    assert simplify_anzsic_code("1123a") == "1123a"

    # structural split
    assert simplify_anzsic_code("1110") == "111"
    assert simplify_anzsic_code("111") == "111"
    assert simplify_anzsic_code("1100") == "11"
    assert simplify_anzsic_code("110") == "11"
    assert simplify_anzsic_code("11") == "11"

    # real examples
    assert simplify_anzsic_code("060") == "06" # Coal mining
    assert simplify_anzsic_code("1212") == "1212" # Beer manufacturing
    assert simplify_anzsic_code("0141a") == "0141a"
    assert simplify_anzsic_code("030a") == "030a" # Native Forestry and Logging, Native Forestry

    # not handled
    # assert simplify_anzsic_code("0301a") == "030a1a" # Native Forestry and Logging, Native Forestry

def test_is_anzsic_code_in_code_family():
    test_family = [
        "060", # Coal mining
        "070", # Oil and gas extraction
        "292", # Waste treatment, disposal and remediation services
    ]

    assert is_anzsic_code_in_code_family("06", test_family) == True
    assert is_anzsic_code_in_code_family("060", test_family) == True
    assert is_anzsic_code_in_code_family("0600", test_family) == True
    assert is_anzsic_code_in_code_family("0610", test_family) == True
    assert is_anzsic_code_in_code_family("0611", test_family) == True
    assert is_anzsic_code_in_code_family("07", test_family) == True
    assert is_anzsic_code_in_code_family("0711", test_family) == True
    assert is_anzsic_code_in_code_family("292", test_family) == True
    assert is_anzsic_code_in_code_family("2921", test_family) == True

    assert is_anzsic_code_in_code_family("08", test_family) == False
    assert is_anzsic_code_in_code_family("080", test_family) == False
    assert is_anzsic_code_in_code_family("0800", test_family) == False
    assert is_anzsic_code_in_code_family("0810", test_family) == False
    assert is_anzsic_code_in_code_family("29", test_family) == False
    assert is_anzsic_code_in_code_family("293", test_family) == False

    # not handled
    # assert is_anzsic_code_in_code_family("030a1a", ["0301a"]) == True # Native Forestry and Logging, Native Forestry

