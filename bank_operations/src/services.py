import json
import logging
import math
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# разные форматы: +7 (900) 000-00-00, 89000000000, +7 921 11-22-33
PHONE_PATTERN = re.compile(
    r"(?:\+7|8)"
    r"[\s\-]?"
    r"\(?\d{3}\)?"
    r"[\s\-]?"
    r"\d{2,3}"
    r"[\s\-]?"
    r"\d{2}"
    r"[\s\-]?"
    r"\d{2}"
)

PERSON_PATTERN = re.compile(r"^[А-ЯЁA-Z][а-яёa-z]+ [А-ЯЁA-Z]\.$")


def _as_records(data):
    """Список словарей из датафрейма или списка."""
    if hasattr(data, "to_dict"):
        return data.to_dict(orient="records")
    return list(data)


def profitable_categories(data, year, month):
    """Сколько кешбэка можно получить по категориям за месяц (1%)."""
    logger.info("Считаем выгодные категории для %s-%s", year, month)
    records = _as_records(data)
    cashback = {}

    def is_needed_month(item):
        date_value = item.get("Дата операции")
        if date_value is None:
            return False
        if hasattr(date_value, "year"):
            return date_value.year == int(year) and date_value.month == int(month)
        text = str(date_value)
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            try:
                parsed = datetime.strptime(text[:10], "%d.%m.%Y")
            except ValueError:
                return False
        return parsed.year == int(year) and parsed.month == int(month)

    month_items = list(filter(is_needed_month, records))

    for item in month_items:
        amount = item.get("Сумма платежа", item.get("Сумма операции", 0))
        try:
            amount = float(str(amount).replace(",", "."))
        except ValueError:
            amount = 0.0
        if amount >= 0:
            continue
        category = item.get("Категория")
        if category is None or str(category) == "nan":
            continue
        category = str(category)
        if category not in cashback:
            cashback[category] = 0.0
        cashback[category] += abs(amount) / 100

    # округляем до целых, как обычно ждут в отчете
    result = {}
    for name, value in cashback.items():
        result[name] = int(round(value))

    result = dict(sorted(result.items(), key=lambda item: item[1], reverse=True))
    logger.info("Категорий с кешбэком: %s", len(result))
    return json.dumps(result, ensure_ascii=False, indent=2)


def investment_bank(month, transactions, limit):
    """Сколько удалось бы отложить в Инвесткопилку."""
    logger.info("Инвесткопилка за %s, шаг %s", month, limit)
    total = 0.0

    def in_month(item):
        date_value = str(item.get("Дата операции", ""))
        return date_value.startswith(month) or month in date_value[:7]

    month_items = list(filter(in_month, transactions))

    for item in month_items:
        try:
            amount = float(item.get("Сумма операции", 0))
        except (TypeError, ValueError):
            continue
        amount = abs(amount)
        if amount == 0:
            continue
        remainder = amount % limit
        if remainder != 0:
            total += limit - remainder

    return round(total, 2)


def simple_search(data, query):
    """Поиск по подстроке в описании или категории, без учета регистра."""
    logger.info("Поиск: %s", query)
    records = _as_records(data)
    needle = str(query).lower()

    def matches(item):
        description = str(item.get("Описание", "")).lower()
        category = str(item.get("Категория", "")).lower()
        return needle in description or needle in category

    found = list(filter(matches, records))
    # даты лучше отдать строкой
    clean = []
    for item in found:
        row = {}
        for key, value in item.items():
            if hasattr(value, "strftime"):
                row[key] = value.strftime("%d.%m.%Y %H:%M:%S")
            elif isinstance(value, float) and math.isnan(value):
                row[key] = None
            else:
                row[key] = value
        clean.append(row)

    logger.info("Найдено транзакций: %s", len(clean))
    return json.dumps(clean, ensure_ascii=False, indent=2)


def phone_number_search(data):
    """Ищет транзакции, где в описании есть мобильный номер."""
    logger.info("Поиск по телефонным номерам")
    records = _as_records(data)

    def has_phone(item):
        description = str(item.get("Описание", ""))
        return PHONE_PATTERN.search(description) is not None

    found = list(filter(has_phone, records))
    clean = []
    for item in found:
        row = {}
        for key, value in item.items():
            if hasattr(value, "strftime"):
                row[key] = value.strftime("%d.%m.%Y %H:%M:%S")
            else:
                row[key] = value
        clean.append(row)

    logger.info("Транзакций с телефонами: %s", len(clean))
    return json.dumps(clean, ensure_ascii=False, indent=2)


def person_transfers_search(data):
    """Переводы физлицам: категория Переводы и имя вида 'Иван П.'."""
    logger.info("Поиск переводов физлицам")
    records = _as_records(data)

    def is_person(item):
        category = str(item.get("Категория", ""))
        description = str(item.get("Описание", "")).strip()
        if category != "Переводы":
            return False
        return PERSON_PATTERN.match(description) is not None

    found = list(filter(is_person, records))
    clean = []
    for item in found:
        row = {}
        for key, value in item.items():
            if hasattr(value, "strftime"):
                row[key] = value.strftime("%d.%m.%Y %H:%M:%S")
            else:
                row[key] = value
        clean.append(row)

    logger.info("Переводов физлицам: %s", len(clean))
    return json.dumps(clean, ensure_ascii=False, indent=2)
