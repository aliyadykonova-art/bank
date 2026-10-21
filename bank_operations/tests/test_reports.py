from datetime import datetime

import pandas as pd

from src.reports import spending_by_category, spending_by_weekday, spending_by_workday


def test_spending_by_category(sample_transactions):
    result = spending_by_category(sample_transactions, "Супермаркеты", "2021-12-20")
    assert isinstance(result, pd.DataFrame)
    assert len(result) >= 1
    assert set(result["Категория"].unique()) == {"Супермаркеты"}


def test_spending_by_weekday(sample_transactions):
    result = spending_by_weekday(sample_transactions, datetime(2021, 12, 20))
    assert "weekday_name" in result.columns
    assert "spent" in result.columns
    assert len(result) >= 1


def test_spending_by_workday(sample_transactions):
    result = spending_by_workday(sample_transactions, "2021-12-20")
    types = list(result["day_type"])
    assert "Рабочий день" in types
    assert "Выходной день" in types
