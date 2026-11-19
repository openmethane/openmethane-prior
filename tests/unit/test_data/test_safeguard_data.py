import io

import pandas as pd
import pytest

from openmethane_prior.data_sources.financial_year import FinancialYear
from openmethane_prior.data_sources.safeguard.data import (
    SafeguardBaselinesAndEmissionsTable,
    parse_csv_text,
    read_baselines_and_emissions_csv,
)

# header as published by the CER for FY 2023-24 and FY 2024-25
published_header = (
    "Facility name,Responsible emitter,State/Territory of operation,ANZSIC,ERC,"
    "Baseline emissions number,Covered emissions,Borrowing adjustment amount,ACCUs issued,"
    "ACCUs deemed surrendered,ACCUs surrendered,SMCs surrendered,Net emissions number,"
    "Net position number,SMCs issued,Units relinquished,Cumulative MYMP net emissions number,"
    "Cumulative MYMP net position number,GHG Carbon dioxide,GHG Methane,GHG Nitrous oxide,"
    "GHG Other,Notes"
)


def test_safeguard_table_file_name():
    table = SafeguardBaselinesAndEmissionsTable(
        financial_year=FinancialYear(2024),
        url="https://example.com/2024-25",
        ch4_gwp=28,
        co2_gwp=1,
    )

    assert table.file_name == "2024-25-baselines-and-emissions-table.csv"


def test_parse_csv_text():
    assert parse_csv_text("  Arrow Surat Operations ") == "Arrow Surat Operations"


def test_read_baselines_and_emissions_csv():
    csv = (
        published_header + "\n"
        + 'Mine A,Emitter A,QLD,Coal mining (060),0.9,"100,000","90,000",0,0,0,0,0,'
        + '"90,000","-10,000",0,0,-,-,"12,000"," 1,551 ",45,10,Notes\n'
        + 'Mine B ,Emitter B,NSW,Coal mining (060),0.9,0,0,0,0,0,0,0,0,0,0,0,-,-,0,-,0,0,-\n'
    )

    result = read_baselines_and_emissions_csv(io.BytesIO(csv.encode("cp1252")))

    expected = pd.DataFrame({
        "facility_name": ["Mine A", "Mine B"],
        "state": ["QLD", "NSW"],
        "anzsic": ["Coal mining (060)", "Coal mining (060)"],
        "co2e_ch4": [1551.0, None],
    })
    pd.testing.assert_frame_equal(result, expected)


def test_read_baselines_and_emissions_csv_reordered_columns():
    csv = (
        "GHG Methane,Notes,ANZSIC,Facility name,State/Territory of operation\n"
        + '"2,000",-,Oil and gas extraction (070),Field A,WA\n'
    )

    result = read_baselines_and_emissions_csv(io.BytesIO(csv.encode("cp1252")))

    assert list(result.columns) == ["facility_name", "state", "anzsic", "co2e_ch4"]
    assert result.iloc[0].to_dict() == {
        "facility_name": "Field A",
        "state": "WA",
        "anzsic": "Oil and gas extraction (070)",
        "co2e_ch4": 2000.0,
    }


def test_read_baselines_and_emissions_csv_missing_column():
    csv = "Facility name,State/Territory of operation,ANZSIC\nMine A,QLD,Coal mining (060)\n"

    with pytest.raises(ValueError):
        read_baselines_and_emissions_csv(io.BytesIO(csv.encode("cp1252")))
