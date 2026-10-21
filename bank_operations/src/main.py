import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.reports import spending_by_category, spending_by_weekday, spending_by_workday
from src.services import (
    investment_bank,
    person_transfers_search,
    phone_number_search,
    profitable_categories,
    simple_search,
)
from src.utils import load_transactions
from src.views import get_events_page, get_home_page


def run():
    print("Загружаю операции...")
    data = load_transactions()

    print("\n=== Главная ===")
    home = get_home_page(data, "2021-12-20 15:30:00")
    print(home)

    print("\n=== События за месяц ===")
    events = get_events_page(data, "2021-12-20 15:30:00", "M")
    print(events)

    print("\n=== Выгодные категории кешбэка ===")
    print(profitable_categories(data, 2021, 12))

    print("\n=== Простой поиск: магнит ===")
    print(simple_search(data, "магнит"))

    print("\n=== Поиск по телефонам ===")
    print(phone_number_search(data))

    print("\n=== Переводы физлицам ===")
    print(person_transfers_search(data))

    print("\n=== Инвесткопилка ===")
    records = data.to_dict(orient="records")
    saved = investment_bank("2021-12", records, 50)
    print(saved)

    print("\n=== Отчеты ===")
    spending_by_category(data, "Супермаркеты", "2021-12-20")
    spending_by_weekday(data, "2021-12-20")
    spending_by_workday(data, "2021-12-20")
    print("Отчеты записаны в папку reports")


if __name__ == "__main__":
    run()
