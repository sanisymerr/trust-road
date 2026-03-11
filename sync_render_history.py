from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
HISTORY_DIR = DATA_DIR / "history"
LATEST_PATH = DATA_DIR / "latest_rates.json"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Поставь сюда свой публичный Render URL
DEFAULT_BASE_URL = "https://trust-road.onrender.com"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def load_local_dates() -> list[str]:
    if not HISTORY_DIR.exists():
        return []

    dates = [file.stem for file in HISTORY_DIR.glob("*.json") if file.is_file()]
    dates.sort(reverse=True)
    return dates


def get_json(url: str) -> dict:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def fetch_remote_dates(base_url: str) -> dict:
    return get_json(f"{base_url}/api/history/dates")


def fetch_remote_latest(base_url: str) -> dict:
    return get_json(f"{base_url}/api/latest.json")


def fetch_remote_date(base_url: str, date_value: str) -> dict | None:
    response = requests.get(f"{base_url}/api/history/{date_value}.json", timeout=60)

    if response.status_code == 404:
        return None

    response.raise_for_status()
    return response.json()


def save_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def print_status(base_url: str) -> None:
    ensure_dirs()

    remote_info = fetch_remote_dates(base_url)
    remote_dates = remote_info.get("available_dates", [])
    local_dates = load_local_dates()

    remote_set = set(remote_dates)
    local_set = set(local_dates)

    missing_local = [date for date in remote_dates if date not in local_set]
    missing_remote = [date for date in local_dates if date not in remote_set]

    print(f"Render URL: {base_url}")
    print(f"Доступно дат на Render: {len(remote_dates)}")
    print(f"Локально дат: {len(local_dates)}")
    print(f"Последняя дата на Render: {remote_info.get('latest_date')}")
    print(f"Последнее обновление на Render: {remote_info.get('updated_at_vladivostok')}")
    print()

    print("Даты на Render:")
    if remote_dates:
        print(", ".join(remote_dates))
    else:
        print("—")
    print()

    print("Не хватает локально:")
    if missing_local:
        print(", ".join(missing_local))
    else:
        print("Нет, всё синхронизировано.")
    print()

    print("Есть локально, но нет на Render:")
    if missing_remote:
        print(", ".join(missing_remote))
    else:
        print("Нет.")


def pull_date(base_url: str, date_value: str, overwrite: bool = False) -> bool:
    if not DATE_RE.fullmatch(date_value):
        print(f"[skip] Некорректная дата: {date_value}")
        return False

    payload = fetch_remote_date(base_url, date_value)
    if payload is None:
        print(f"[skip] На Render нет даты {date_value}")
        return False

    destination = HISTORY_DIR / f"{date_value}.json"

    if destination.exists() and not overwrite:
        print(f"[skip] Уже есть локально: {date_value}")
        return False

    save_json(destination, payload)
    print(f"[ok] Сохранено: {destination}")
    return True


def pull_missing(base_url: str, overwrite: bool = False) -> None:
    ensure_dirs()

    remote_info = fetch_remote_dates(base_url)
    remote_dates = remote_info.get("available_dates", [])
    local_set = set(load_local_dates())

    missing_dates = [date for date in remote_dates if date not in local_set]

    if not missing_dates:
        print("Недостающих дат нет.")
    else:
        for date_value in missing_dates:
            pull_date(base_url, date_value, overwrite=overwrite)

    latest_payload = fetch_remote_latest(base_url)
    save_json(LATEST_PATH, latest_payload)
    print(f"[ok] Обновлён latest: {LATEST_PATH}")


def pull_selected_dates(base_url: str, dates: list[str], overwrite: bool = False) -> None:
    ensure_dirs()

    for date_value in dates:
        pull_date(base_url, date_value, overwrite=overwrite)

    latest_payload = fetch_remote_latest(base_url)
    save_json(LATEST_PATH, latest_payload)
    print(f"[ok] Обновлён latest: {LATEST_PATH}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Синхронизация history JSON с Render"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Базовый URL сайта на Render, например https://trust-road.onrender.com",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Показать даты на Render и чего не хватает локально")

    pull_missing_parser = subparsers.add_parser(
        "pull-missing",
        help="Скачать все даты, которых не хватает локально",
    )
    pull_missing_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Перезаписывать уже существующие локальные файлы",
    )

    pull_date_parser = subparsers.add_parser(
        "pull-date",
        help="Скачать одну или несколько конкретных дат",
    )
    pull_date_parser.add_argument("dates", nargs="+", help="Например: 2026-03-12")
    pull_date_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Перезаписывать уже существующие локальные файлы",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    if args.command == "status":
        print_status(base_url)
        return

    if args.command == "pull-missing":
        pull_missing(base_url, overwrite=args.overwrite)
        return

    if args.command == "pull-date":
        pull_selected_dates(base_url, args.dates, overwrite=args.overwrite)
        return


if __name__ == "__main__":
    main()