import datetime

import pytest

from openmethane_prior.data_sources.financial_year import FinancialYear


def test_financial_year_label():
    assert FinancialYear(2023).label == "2023-24"
    assert FinancialYear(2099).label == "2099-00"


def test_financial_year_str():
    assert str(FinancialYear(2023)) == "2023-24"
    assert f"FY {FinancialYear(2024)}" == "FY 2024-25"


def test_financial_year_start_and_end():
    financial_year = FinancialYear(2023)

    assert financial_year.start == datetime.date(2023, 7, 1)
    assert financial_year.end == datetime.date(2024, 6, 30)


@pytest.mark.parametrize("date", [
    datetime.date(2023, 7, 1),
    datetime.date(2023, 12, 31),
    datetime.date(2024, 1, 1),
    datetime.date(2024, 6, 30),
])
def test_financial_year_from_date(date):
    assert FinancialYear.from_date(date) == FinancialYear(2023)


def test_financial_year_from_period():
    result = FinancialYear.from_period(datetime.date(2024, 6, 1), datetime.date(2024, 6, 30))

    assert result == FinancialYear(2023)


def test_financial_year_from_period_spans_financial_years():
    with pytest.raises(ValueError, match="must be within the same financial year"):
        FinancialYear.from_period(datetime.date(2024, 6, 30), datetime.date(2024, 7, 1))


def test_financial_year_from_label():
    assert FinancialYear.from_label("2024-25") == FinancialYear(2024)
    assert FinancialYear.from_label(" 2099-00 ") == FinancialYear(2099)


@pytest.mark.parametrize("label", ["2024-2025", "2024-26", "2024/25", "FY24", ""])
def test_financial_year_from_label_invalid(label):
    with pytest.raises(ValueError, match="invalid financial year"):
        FinancialYear.from_label(label)


def test_financial_year_order():
    assert sorted([FinancialYear(2024), FinancialYear(2023)]) == [
        FinancialYear(2023), FinancialYear(2024),
    ]
