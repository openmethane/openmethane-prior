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


def test_simplify_anzsic_code_preserves_subdivision():
    # subdivision codes ending in 0 must not be shortened to a single digit
    assert simplify_anzsic_code("30") == "30"
    assert simplify_anzsic_code("3000") == "30"
    assert simplify_anzsic_code("20") == "20"
    assert simplify_anzsic_code("2000") == "20"


def test_filter_by_anzsic_code_family_coal_mining():
    df = pd.DataFrame({"anzsic_code": ["06", "060", "0600", "061", "0612", "1212", "9999"]})
    filtered = filter_by_anzsic_code_family(df, ["06"], column="anzsic_code")
    assert list(filtered["anzsic_code"]) == ["06", "060", "0600", "061", "0612"]


def test_filter_by_anzsic_code_family_nuanced():
    df = pd.DataFrame({"anzsic_code": ["202", "2021", "2029", "20", "201", "22", "1212"]})
    filtered = filter_by_anzsic_code_family(df, ["202"], column="anzsic_code")
    assert list(filtered["anzsic_code"]) == ["202", "2021", "2029"]


def test_filter_by_anzsic_code_family_subdivision_boundaries():
    df = pd.DataFrame({"anzsic_code": ["3010", "3110", "3020", "3100"]})
    filtered = filter_by_anzsic_code_family(df, ["30"], column="anzsic_code")
    assert list(filtered["anzsic_code"]) == ["3010", "3020"]


def test_filter_by_anzsic_code_family_padded_codes():
    df = pd.DataFrame({"anzsic_code": ["2110", "2120", "2021", "2200", "9999"]})
    by_short = filter_by_anzsic_code_family(df, ["21"], column="anzsic_code")
    by_padded = filter_by_anzsic_code_family(df, ["2100"], column="anzsic_code")
    assert list(by_short["anzsic_code"]) == list(by_padded["anzsic_code"]) == ["2110", "2120"]

    # group-level: 2020 and 202 are equivalent; exclude subdivision/group siblings
    df_group = pd.DataFrame({"anzsic_code": ["20", "201", "202", "2021", "2029", "22"]})
    by_group = filter_by_anzsic_code_family(df_group, ["202"], column="anzsic_code")
    by_padded_group = filter_by_anzsic_code_family(df_group, ["2020"], column="anzsic_code")
    assert list(by_group["anzsic_code"]) == list(by_padded_group["anzsic_code"]) == ["202", "2021", "2029"]

    # subdivision-level: 2000 and 20 are equivalent; match entire subdivision 20
    by_subdivision = filter_by_anzsic_code_family(df_group, ["20"], column="anzsic_code")
    by_padded_subdivision = filter_by_anzsic_code_family(df_group, ["2000"], column="anzsic_code")
    assert (
        list(by_subdivision["anzsic_code"])
        == list(by_padded_subdivision["anzsic_code"])
        == ["20", "201", "202", "2021", "2029"]
    )

    df_outside_subdivision = pd.DataFrame({"anzsic_code": ["2021", "2030", "2120", "3020"]})
    filtered = filter_by_anzsic_code_family(df_outside_subdivision, ["2000"], column="anzsic_code")
    assert list(filtered["anzsic_code"]) == ["2021", "2030"]


def test_filter_by_anzsic_code_family_multiple_families():
    df = pd.DataFrame({"anzsic_code": ["0600", "1212", "0700", "9999"]})
    filtered = filter_by_anzsic_code_family(df, ["06", "07"], column="anzsic_code")
    assert list(filtered["anzsic_code"]) == ["0600", "0700"]


def test_filter_by_anzsic_code_family_empty_codes():
    df = pd.DataFrame({"anzsic_code": ["0600"]})
    filtered = filter_by_anzsic_code_family(df, [], column="anzsic_code")
    assert len(filtered) == len(df)
