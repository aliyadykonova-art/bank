import json

from src.services import (
    investment_bank,
    person_transfers_search,
    phone_number_search,
    profitable_categories,
    simple_search,
)


def test_profitable_categories(sample_transactions):
    raw = profitable_categories(sample_transactions, 2021, 12)
    data = json.loads(raw)
    assert isinstance(data, dict)
    assert len(data) >= 3
    # 1% от 1500 = 15
    assert data["Супермаркеты"] == 15
    values = list(data.values())
    assert values == sorted(values, reverse=True)


def test_simple_search_case_insensitive(sample_transactions):
    raw = simple_search(sample_transactions, "мАгНиТ")
    data = json.loads(raw)
    assert len(data) >= 1
    text = json.dumps(data, ensure_ascii=False).lower()
    assert "магнит" in text


def test_simple_search_by_category(sample_transactions):
    raw = simple_search(sample_transactions, "фастфуд")
    data = json.loads(raw)
    assert len(data) == 1
    assert data[0]["Описание"] == "Бургер Кинг"


def test_phone_number_search(sample_transactions):
    raw = phone_number_search(sample_transactions)
    data = json.loads(raw)
    descriptions = [item["Описание"] for item in data]
    assert any("+7 (900) 000-00-00" in text for text in descriptions)
    assert any("89000000000" in text for text in descriptions)
    assert any("+7 921 11-22-33" in text for text in descriptions)
    assert any("+7 995 555-55-55" in text for text in descriptions)
    assert len(data) >= 4


def test_person_transfers_search(sample_transactions):
    raw = person_transfers_search(sample_transactions)
    data = json.loads(raw)
    names = [item["Описание"] for item in data]
    assert "Константин Л." in names
    assert "Сергей З." in names
    for item in data:
        assert item["Категория"] == "Переводы"


def test_investment_bank():
    transactions = [
        {"Дата операции": "2021-12-01", "Сумма операции": 1712},
        {"Дата операции": "2021-12-02", "Сумма операции": 50},
        {"Дата операции": "2021-11-02", "Сумма операции": 1712},
    ]
    # 1712 -> до 1750, в копилку 38; 50 уже круглое
    assert investment_bank("2021-12", transactions, 50) == 38.0
