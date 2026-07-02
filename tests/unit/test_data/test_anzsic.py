import pandas as pd

from openmethane_prior.data_sources.safeguard.anzsic import (
    filter_by_anzsic_code_family,
    simplify_anzsic_code,
)


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


def test_filter_by_anzsic_code_family_coal_mining():
    df = pd.DataFrame({"anzsic_code": ["06", "060", "0600", "061", "0612", "1212", "9999"]})
    filtered = filter_by_anzsic_code_family(df, ["06"], column="anzsic_code")
    assert list(filtered["anzsic_code"]) == ["06", "060", "0600", "061", "0612"]


def test_filter_by_anzsic_code_family_nuanced():
    df = pd.DataFrame({"anzsic_code": ["202", "2021", "2029", "20", "201", "22", "1212"]})
    filtered = filter_by_anzsic_code_family(df, ["202"], column="anzsic_code")
    assert list(filtered["anzsic_code"]) == ["202", "2021", "2029"]


def test_filter_by_anzsic_code_family_multiple_families():
    df = pd.DataFrame({"anzsic_code": ["0600", "1212", "0700", "9999"]})
    filtered = filter_by_anzsic_code_family(df, ["06", "07"], column="anzsic_code")
    assert list(filtered["anzsic_code"]) == ["0600", "0700"]


def test_filter_by_anzsic_code_family_empty_codes():
    df = pd.DataFrame({"anzsic_code": ["0600"]})
    filtered = filter_by_anzsic_code_family(df, [], column="anzsic_code")
    assert len(filtered) == len(df)
