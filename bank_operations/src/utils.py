import json
import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
LOGS_DIR = ROOT_DIR / "logs"
SETTINGS_PATH = ROOT_DIR / "user_settings.json"
OPERATIONS_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1yXnr282zAMcTkEhIwZFaJlPJvAeZIwvB/export?format=csv"
)

LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOGS_DIR / "app.log"),
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger(__name__)

CBR_URL = os.getenv("CBR_URL", "https://www.cbr-xml-daily.ru/daily_json.js")
YAHOO_CHART_URL = os.getenv(
    "YAHOO_CHART_URL",
    "https://query1.finance.yahoo.com/v8/finance/chart",
)

# запасные значения, если API не ответил
FALLBACK_RATES = {"USD": 90.0, "EUR": 100.0}
FALLBACK_STOCK_PRICE = 100.0


def load_user_settings(path=None):
    """Читает валюты и акции из файла настроек."""
    file_path = Path(path) if path else SETTINGS_PATH
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            settings = json.load(file)
        return settings
    except Exception as error:
        logger.error("Не удалось прочитать настройки: %s", error)
        return {
            "user_currencies": ["USD", "EUR"],
            "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"],
        }


def parse_date(date_text, end_of_day=False):
    """Превращает строку с датой в datetime."""
    if isinstance(date_text, datetime):
        return date_text

    text = str(date_text).strip()
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y",
    ]
    date_only = ["%Y-%m-%d", "%d.%m.%Y"]
    for fmt in formats:
        try:
            value = datetime.strptime(text, fmt)
            if end_of_day and fmt in date_only:
                value = value.replace(hour=23, minute=59, second=59)
            return value
        except ValueError:
            continue

    logger.error("Не получилось разобрать дату: %s", date_text)
    raise ValueError("Неверный формат даты")


def get_greeting(date_time):
    """Приветствие по часу."""
    hour = date_time.hour
    if 6 <= hour <= 11:
        return "Доброе утро"
    if 12 <= hour <= 17:
        return "Добрый день"
    if 18 <= hour <= 22:
        return "Добрый вечер"
    return "Доброй ночи"


def to_float(value):
    """Переводит сумму из Excel/CSV в число."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace(" ", "").replace("\xa0", "")
    if text == "" or text.lower() == "nan":
        return 0.0
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        logger.warning("Не число: %s", value)
        return 0.0


def get_last_digits(card):
    """Берет последние 4 цифры номера карты."""
    if card is None or (isinstance(card, float) and pd.isna(card)):
        return None

    digits = ""
    for ch in str(card):
        if ch.isdigit():
            digits += ch

    if digits == "":
        return None
    if len(digits) >= 4:
        return digits[-4:]
    return digits


def _prepare_dataframe(df):
    """Чистит названия колонок и типы данных."""
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]

    if "Дата операции" in df.columns:
        df["Дата операции"] = pd.to_datetime(
            df["Дата операции"],
            dayfirst=True,
            errors="coerce",
        )

    for column in ["Сумма операции", "Сумма платежа", "Кэшбэк", "Кешбэк"]:
        if column in df.columns:
            df[column] = df[column].apply(to_float)

    return df


def download_operations_csv(save_path):
    """Скачивает таблицу операций, если файла еще нет."""
    logger.info("Скачиваю operations.csv")
    response = requests.get(OPERATIONS_URL, timeout=30)
    response.raise_for_status()
    save_path.parent.mkdir(exist_ok=True)
    with open(save_path, "wb") as file:
        file.write(response.content)
    return save_path


def load_transactions(file_path=None):
    """Читает транзакции из Excel или CSV."""
    if file_path is None:
        xlsx_path = DATA_DIR / "operations.xlsx"
        xls_path = DATA_DIR / "operations.xls"
        csv_path = DATA_DIR / "operations.csv"
        if xlsx_path.exists():
            file_path = xlsx_path
        elif xls_path.exists():
            file_path = xls_path
        else:
            file_path = csv_path
    else:
        file_path = Path(file_path)

    if not file_path.exists():
        try:
            download_operations_csv(file_path)
        except Exception as error:
            logger.error("Не удалось скачать файл операций: %s", error)
            raise FileNotFoundError("Файл с операциями не найден") from error

    suffix = file_path.suffix.lower()
    try:
        if suffix in [".xlsx", ".xls"]:
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
        df = _prepare_dataframe(df)
        logger.info("Загружено транзакций: %s", len(df))
        return df
    except Exception as error:
        logger.error("Ошибка чтения файла: %s", error)
        raise


def filter_by_date_range(df, start_date, end_date):
    """Оставляет операции с начала диапазона по конечную дату."""
    result = df.copy()
    result = result[result["Дата операции"].notna()]
    result = result[
        (result["Дата операции"] >= start_date)
        & (result["Дата операции"] <= end_date)
    ]
    if "Статус" in result.columns:
        result = result[result["Статус"] == "OK"]
    return result.reset_index(drop=True)


def get_period_range(date_time, period="M"):
    """Считает начало и конец периода для страницы События."""
    end_date = date_time
    period = (period or "M").upper()

    if period == "W":
        start_date = date_time.replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = start_date - pd.Timedelta(days=date_time.weekday())
    elif period == "Y":
        start_date = date_time.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
    elif period == "ALL":
        start_date = datetime(2000, 1, 1)
    else:
        start_date = date_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return start_date, end_date


def get_currency_rates(currencies):
    """Курс валют с сайта ЦБ. Если ошибка — берем запасные числа."""
    result = []
    rates = {}

    try:
        response = requests.get(CBR_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        valute = data.get("Valute", {})
        for code in currencies:
            if code in valute:
                rates[code] = float(valute[code]["Value"])
        logger.info("Курсы валют получены")
    except Exception as error:
        logger.error("Ошибка API валют: %s", error)

    for code in currencies:
        rate = rates.get(code, FALLBACK_RATES.get(code, 1.0))
        if rate is None or rate <= 0:
            rate = 1.0
        result.append({"currency": code, "rate": float(rate)})

    return result


def get_stock_prices(stocks):
    """Цены акций. Если API не ответил, ставим запасную цену."""
    result = []
    headers = {"User-Agent": "Mozilla/5.0"}

    for ticker in stocks:
        price = None
        try:
            url = f"{YAHOO_CHART_URL}/{ticker}"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            meta = data["chart"]["result"][0]["meta"]
            price = float(meta.get("regularMarketPrice"))
            logger.info("Цена %s получена", ticker)
        except Exception as error:
            logger.error("Ошибка API акций для %s: %s", ticker, error)

        if price is None or price <= 0:
            price = float(FALLBACK_STOCK_PRICE)

        result.append({"stock": str(ticker), "price": float(price)})

    return result
