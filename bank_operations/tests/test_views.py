import json
from unittest.mock import patch

from src.views import get_events_page, get_home_page


FAKE_RATES = [{"currency": "USD", "rate": 73.21}, {"currency": "EUR", "rate": 87.08}]
FAKE_STOCKS = [
    {"stock": "AAPL", "price": 150.12},
    {"stock": "AMZN", "price": 3173.18},
    {"stock": "GOOGL", "price": 2742.39},
    {"stock": "MSFT", "price": 296.71},
    {"stock": "TSLA", "price": 1007.08},
]


@patch("src.views.get_stock_prices", return_value=FAKE_STOCKS)
@patch("src.views.get_currency_rates", return_value=FAKE_RATES)
def test_home_page(mock_rates, mock_stocks, sample_transactions):
    raw = get_home_page(sample_transactions, "2021-12-20 15:30:00")
    data = json.loads(raw)

    assert data["greeting"] == "Добрый день"
    assert len(data["cards"]) >= 1
    card = data["cards"][0]
    assert "last_digits" in card
    assert "total_spent" in card
    assert "cashback" in card
    assert card["cashback"] == round(card["total_spent"] / 100, 2)

    assert len(data["top_transactions"]) == 5
    amounts = [item["amount"] for item in data["top_transactions"]]
    assert amounts == sorted(amounts, reverse=True)
    for item in data["top_transactions"]:
        assert "date" in item
        assert "amount" in item
        assert "category" in item
        assert "description" in item
        assert item["date"][2] == "."
        assert item["date"][5] == "."
        assert len(item["date"]) == 10

    assert data["currency_rates"] == FAKE_RATES
    assert data["stock_prices"] == FAKE_STOCKS


@patch("src.views.get_stock_prices", return_value=FAKE_STOCKS)
@patch("src.views.get_currency_rates", return_value=FAKE_RATES)
def test_home_page_night(mock_rates, mock_stocks, sample_transactions):
    raw = get_home_page(sample_transactions, "2021-12-20 23:15:00")
    data = json.loads(raw)
    assert data["greeting"] == "Доброй ночи"


@patch("src.views.get_stock_prices", return_value=FAKE_STOCKS)
@patch("src.views.get_currency_rates", return_value=FAKE_RATES)
def test_events_page(mock_rates, mock_stocks, sample_transactions):
    raw = get_events_page(sample_transactions, "2021-12-20 15:30:00", "M")
    data = json.loads(raw)

    assert "expenses" in data
    assert "income" in data
    assert "currency_rates" in data
    assert "stock_prices" in data

    expenses = data["expenses"]
    assert "total_amount" in expenses
    assert "main" in expenses
    assert "transfers_and_cash" in expenses
    assert isinstance(expenses["total_amount"], int)

    categories = [item["category"] for item in expenses["main"]]
    assert "Супермаркеты" in categories
    assert "Остальное" in categories
    # топ-7 обычных категорий + Остальное
    assert categories.count("Остальное") == 1
    assert "Наличные" not in categories
    assert "Переводы" not in categories

    cash_names = [item["category"] for item in expenses["transfers_and_cash"]]
    assert "Наличные" in cash_names
    assert "Переводы" in cash_names

    income_cats = [item["category"] for item in data["income"]["main"]]
    assert "Пополнения" in income_cats
    assert data["income"]["total_amount"] == 21000

    for item in expenses["main"]:
        assert isinstance(item["amount"], int)


@patch("src.views.get_stock_prices", return_value=FAKE_STOCKS)
@patch("src.views.get_currency_rates", return_value=FAKE_RATES)
def test_events_page_all_does_not_take_future(mock_rates, mock_stocks, sample_transactions):
    raw = get_events_page(sample_transactions, "2021-11-30 12:00:00", "ALL")
    data = json.loads(raw)
    # декабрьские траты не должны попасть
    cats = [item["category"] for item in data["expenses"]["main"]]
    assert "Фастфуд" not in cats
