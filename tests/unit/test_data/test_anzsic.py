
from openmethane_prior.data_sources.safeguard.anzsic import simplify_anzsic_code


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
