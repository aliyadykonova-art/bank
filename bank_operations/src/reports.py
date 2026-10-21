import json
import logging
from datetime import datetime
from functools import wraps
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
DEFAULT_REPORT_FILE = REPORTS_DIR / "report.json"


def save_report(filename=None):
    """
    Декоратор для отчетов.
    Без параметра пишет в report.json.
    С параметром пишет в указанный файл.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            path = filename if filename else DEFAULT_REPORT_FILE
            path = Path(path)
            if not path.is_absolute():
                path = REPORTS_DIR / path
            try:
                if isinstance(result, pd.DataFrame):
                    result.to_json(path, orient="records", force_ascii=False, indent=2)
                elif isinstance(result, str):
                    with open(path, "w", encoding="utf-8") as file:
                        file.write(result)
                else:
                    with open(path, "w", encoding="utf-8") as file:
                        json.dump(result, file, ensure_ascii=False, indent=2)
                logger.info("Отчет сохранен в %s", path)
            except Exception as error:
                logger.error("Не удалось сохранить отчет: %s", error)
            return result

        return wrapper

    # если написали @save_report без скобок
    if callable(filename):
        func = filename
        filename = None
        return decorator(func)
    return decorator


def _get_end_date(date):
    if date is None:
        return datetime.now()
    if isinstance(date, datetime):
        return date
    text = str(date).strip()
    formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y"]
    date_only = ["%Y-%m-%d", "%d.%m.%Y"]
    for fmt in formats:
        try:
            value = datetime.strptime(text, fmt)
            if fmt in date_only:
                value = value.replace(hour=23, minute=59, second=59)
            return value
        except ValueError:
            continue
    return datetime.now()


def _last_three_months(df, end_date):
    start_date = end_date - pd.DateOffset(months=3)
    work = df.copy()
    work["Дата операции"] = pd.to_datetime(work["Дата операции"], dayfirst=True, errors="coerce")
    work = work[work["Дата операции"].notna()]
    work = work[(work["Дата операции"] >= start_date) & (work["Дата операции"] <= end_date)]
    return work


@save_report()
def spending_by_category(transactions, category, date=None):
    """Траты по категории за последние три месяца."""
    logger.info("Отчет по категории %s", category)
    end_date = _get_end_date(date)
    work = _last_three_months(transactions, end_date)
    work = work[work["Категория"] == category]
    work = work[work["Сумма платежа"] < 0]
    result = work.copy()
    result["spent"] = result["Сумма платежа"].abs()
    logger.info("Строк в отчете: %s", len(result))
    return result


@save_report("spending_by_weekday.json")
def spending_by_weekday(transactions, date=None):
    """Средние траты по дням недели за три месяца."""
    logger.info("Отчет по дням недели")
    end_date = _get_end_date(date)
    work = _last_three_months(transactions, end_date)
    work = work[work["Сумма платежа"] < 0].copy()
    work["spent"] = work["Сумма платежа"].abs()
    work["weekday"] = work["Дата операции"].dt.dayofweek
    grouped = work.groupby("weekday")["spent"].mean().reset_index()
    names = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье",
    }
    grouped["weekday_name"] = grouped["weekday"].map(names)
    grouped["spent"] = grouped["spent"].round(2)
    return grouped


@save_report("spending_by_workday.json")
def spending_by_workday(transactions, date=None):
    """Средние траты в рабочий и выходной день."""
    logger.info("Отчет рабочий/выходной")
    end_date = _get_end_date(date)
    work = _last_three_months(transactions, end_date)
    work = work[work["Сумма платежа"] < 0].copy()
    work["spent"] = work["Сумма платежа"].abs()
    work["is_weekend"] = work["Дата операции"].dt.dayofweek >= 5

    rows = []
    workdays = work[work["is_weekend"].eq(False)]
    weekends = work[work["is_weekend"].eq(True)]

    work_avg = 0.0
    week_avg = 0.0
    if len(workdays) > 0:
        work_avg = round(float(workdays["spent"].mean()), 2)
    if len(weekends) > 0:
        week_avg = round(float(weekends["spent"].mean()), 2)

    rows.append({"day_type": "Рабочий день", "average_spent": work_avg})
    rows.append({"day_type": "Выходной день", "average_spent": week_avg})
    return pd.DataFrame(rows)
