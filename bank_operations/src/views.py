import json
import logging

from src.utils import (
    filter_by_date_range,
    get_currency_rates,
    get_greeting,
    get_last_digits,
    get_period_range,
    get_stock_prices,
    load_user_settings,
    parse_date,
)

logger = logging.getLogger(__name__)


def _month_range(date_time):
    start = date_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, date_time


def get_cards_info(df):
    """Сумма расходов и кешбэк по каждой карте."""
    cards = []
    if df.empty:
        return cards

    work = df.copy()
    work["last_digits"] = work["Номер карты"].apply(get_last_digits)
    work = work[work["last_digits"].notna()]
    # расходы — отрицательная сумма платежа
    work = work[work["Сумма платежа"] < 0]

    grouped = work.groupby("last_digits")["Сумма платежа"].sum()
    for last_digits, total in grouped.items():
        total_spent = round(abs(float(total)), 2)
        cashback = round(total_spent / 100, 2)
        cards.append(
            {
                "last_digits": str(last_digits),
                "total_spent": total_spent,
                "cashback": cashback,
            }
        )

    cards = sorted(cards, key=lambda item: item["total_spent"], reverse=True)
    return cards


def get_top_transactions(df, count=5):
    """Топ транзакций по сумме платежа."""
    result = []
    if df.empty:
        return result

    work = df.copy()
    work = work.sort_values(by="Сумма платежа", ascending=False)
    work = work.head(count)

    for _, row in work.iterrows():
        oper_date = row["Дата операции"]
        date_text = oper_date.strftime("%d.%m.%Y")
        category = row["Категория"]
        description = row["Описание"]
        if not isinstance(category, str):
            category = ""
        if not isinstance(description, str):
            description = ""
        result.append(
            {
                "date": date_text,
                "amount": round(float(row["Сумма платежа"]), 2),
                "category": category,
                "description": description,
            }
        )
    return result


def get_home_page(transactions, date_time_str):
    """JSON для страницы Главная."""
    logger.info("Строим главную страницу для %s", date_time_str)
    date_time = parse_date(date_time_str)
    start, end = _month_range(date_time)
    period_df = filter_by_date_range(transactions, start, end)

    settings = load_user_settings()
    currencies = settings.get("user_currencies", [])
    stocks = settings.get("user_stocks", [])

    answer = {
        "greeting": get_greeting(date_time),
        "cards": get_cards_info(period_df),
        "top_transactions": get_top_transactions(period_df, 5),
        "currency_rates": get_currency_rates(currencies),
        "stock_prices": get_stock_prices(stocks),
    }
    return json.dumps(answer, ensure_ascii=False, indent=2)


def _sum_by_category(df):
    """Суммы по категориям, округленные до целых."""
    grouped = df.groupby("Категория")["Сумма платежа"].sum()
    items = []
    for category, total in grouped.items():
        name = str(category) if isinstance(category, str) else "Без категории"
        amount = int(round(abs(float(total))))
        items.append({"category": name, "amount": amount})
    items = sorted(items, key=lambda item: item["amount"], reverse=True)
    return items


def _build_main_expenses(items):
    """Топ-7 категорий, остальное складываем в Остальное."""
    cash_names = ["Наличные", "Переводы"]
    main_items = []
    cash_items = []

    for item in items:
        if item["category"] in cash_names:
            cash_items.append(item)
        else:
            main_items.append(item)

    if len(main_items) > 7:
        top = main_items[:7]
        other_sum = 0
        for item in main_items[7:]:
            other_sum += item["amount"]
        top.append({"category": "Остальное", "amount": other_sum})
        main_items = top

    cash_items = sorted(cash_items, key=lambda item: item["amount"], reverse=True)
    return main_items, cash_items


def get_events_page(transactions, date_str, period="M"):
    """JSON для страницы События."""
    logger.info("Строим события для %s, период %s", date_str, period)
    date_time = parse_date(date_str, end_of_day=True)
    start, end = get_period_range(date_time, period)
    period_df = filter_by_date_range(transactions, start, end)

    expenses_df = period_df[period_df["Сумма платежа"] < 0]
    income_df = period_df[period_df["Сумма платежа"] > 0]

    expense_items = _sum_by_category(expenses_df)
    income_items = _sum_by_category(income_df)
    main_expenses, cash_items = _build_main_expenses(expense_items)

    expenses_total = int(round(abs(float(expenses_df["Сумма платежа"].sum()))))
    income_total = int(round(abs(float(income_df["Сумма платежа"].sum()))))

    settings = load_user_settings()
    currencies = settings.get("user_currencies", [])
    stocks = settings.get("user_stocks", [])

    answer = {
        "expenses": {
            "total_amount": expenses_total,
            "main": main_expenses,
            "transfers_and_cash": cash_items,
        },
        "income": {
            "total_amount": income_total,
            "main": income_items,
        },
        "currency_rates": get_currency_rates(currencies),
        "stock_prices": get_stock_prices(stocks),
    }
    return json.dumps(answer, ensure_ascii=False, indent=2)
