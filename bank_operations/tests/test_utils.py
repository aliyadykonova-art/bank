from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.utils import (
    get_currency_rates,
    get_greeting,
    get_last_digits,
    get_period_range,
    get_stock_prices,
    parse_date,
    to_float,
)


def test_greeting_morning():
    assert get_greeting(datetime(2021, 5, 1, 6, 0, 0)) == "Доброе утро"
    assert get_greeting(datetime(2021, 5, 1, 11, 59, 0)) == "Доброе утро"


def test_greeting_day():
    assert get_greeting(datetime(2021, 5, 1, 12, 0, 0)) == "Добрый день"
    assert get_greeting(datetime(2021, 5, 1, 17, 59, 0)) == "Добрый день"


def test_greeting_evening():
    assert get_greeting(datetime(2021, 5, 1, 18, 0, 0)) == "Добрый вечер"
    assert get_greeting(datetime(2021, 5, 1, 22, 59, 0)) == "Добрый вечер"


def test_greeting_night():
    assert get_greeting(datetime(2021, 5, 1, 23, 0, 0)) == "Доброй ночи"
    assert get_greeting(datetime(2021, 5, 1, 5, 59, 0)) == "Доброй ночи"
    assert get_greeting(datetime(2021, 5, 1, 0, 10, 0)) == "Доброй ночи"


def test_parse_date():
    dt = parse_date("2021-12-20 15:30:00")
    assert dt.year == 2021
    assert dt.month == 12
    assert dt.day == 20
    assert dt.hour == 15


def test_parse_date_wrong():
    with pytest.raises(ValueError):
        parse_date("не дата")


def test_to_float():
    assert to_float("-160,89") == -160.89
    assert to_float(10) == 10.0
    assert to_float("") == 0.0


def test_last_digits():
    assert get_last_digits("*7197") == "7197"
    assert get_last_digits("") is None
    assert get_last_digits(None) is None


def test_period_month():
    dt = datetime(2021, 12, 20, 15, 0, 0)
    start, end = get_period_range(dt, "M")
    assert start.day == 1
    assert start.month == 12
    assert end == dt


def test_period_week():
    dt = datetime(2021, 12, 20, 15, 0, 0)  # понедельник
    start, end = get_period_range(dt, "W")
    assert start.day == 20
    assert end == dt


def test_period_year_and_all():
    dt = datetime(2021, 12, 20, 15, 0, 0)
    start_y, end_y = get_period_range(dt, "Y")
    assert start_y.month == 1
    assert start_y.day == 1
    start_all, end_all = get_period_range(dt, "ALL")
    assert start_all.year == 2000
    assert end_all == dt


@patch("src.utils.requests.get")
def test_currency_rates_ok(mock_get):
    mock_get.return_value = Mock(
        json=lambda: {"Valute": {"USD": {"Value": 73.21}, "EUR": {"Value": 87.08}}},
        raise_for_status=lambda: None,
    )
    rates = get_currency_rates(["USD", "EUR"])
    assert len(rates) == 2
    assert rates[0]["currency"] == "USD"
    assert rates[0]["rate"] == 73.21
    assert isinstance(rates[0]["rate"], float)
    assert rates[0]["rate"] > 0


@patch("src.utils.requests.get")
def test_currency_rates_error(mock_get):
    mock_get.side_effect = Exception("сеть недоступна")
    rates = get_currency_rates(["USD", "EUR"])
    assert len(rates) == 2
    for item in rates:
        assert "currency" in item
        assert "rate" in item
        assert item["rate"] > 0


@patch("src.utils.requests.get")
def test_stock_prices_ok(mock_get):
    mock_get.return_value = Mock(
        json=lambda: {"chart": {"result": [{"meta": {"regularMarketPrice": 150.12}}]}},
        raise_for_status=lambda: None,
    )
    prices = get_stock_prices(["AAPL"])
    assert prices[0]["stock"] == "AAPL"
    assert prices[0]["price"] == 150.12
    assert prices[0]["price"] > 0


@patch("src.utils.requests.get")
def test_stock_prices_error(mock_get):
    mock_get.side_effect = Exception("ошибка")
    prices = get_stock_prices(["AAPL", "MSFT"])
    assert len(prices) == 2
    for item in prices:
        assert isinstance(item["stock"], str)
        assert item["price"] > 0
