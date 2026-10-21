"""Скачивает operations.csv в папку data."""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from src.utils import DATA_DIR, download_operations_csv


def main():
    path = DATA_DIR / "operations.csv"
    download_operations_csv(path)
    print("Файл сохранен:", path)


if __name__ == "__main__":
    main()
