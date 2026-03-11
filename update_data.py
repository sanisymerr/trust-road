from __future__ import annotations

from playwright.sync_api import sync_playwright
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import re
import json
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from decimal import Decimal, getcontext
getcontext().prec = 50
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
JSON_PATH = DATA_DIR / "latest_rates.json"
HISTORY_DIR = DATA_DIR / "history"

TRACKED = ["USD", "EUR", "CNY", "JPY", "KRW", "GBP", "CHF", "SGD", "HKD", "MNT", "RUB"]
CURRENCY_NAMES = {
    "USD": "Доллар США",
    "EUR": "Евро",
    "CNY": "Китайский юань",
    "JPY": "Японская иена",
    "KRW": "Южнокорейская вона",
    "GBP": "Фунт стерлингов",
    "CHF": "Швейцарский франк",
    "SGD": "Сингапурский доллар",
    "HKD": "Гонконгский доллар",
    "MNT": "Монгольский тугрик",
    "RUB": "Российский рубль",
}


# Функция для получения данных о курсах валют с сайта Capitron Bank
# Используем именно ту структуру, которую прислал пользователь.
def get_currency_data() -> list[list[str]]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("https://www.capitronbank.mn/p/exchange?lang=&type=", timeout=60000)
        page.wait_for_selector("table", timeout=60000)

        rows = page.query_selector_all("table tr")
        data: list[list[str]] = []

        for row in rows[1:]:
            cols = row.query_selector_all("td")
            if len(cols) > 0:
                currency = cols[0].text_content().strip()
                bank_rate = cols[2].text_content().strip()
                sell_rate = cols[6].text_content().strip()

                if currency not in ["ZAU", "ZAG"]:
                    data.append([currency, bank_rate, sell_rate])

        browser.close()
        return data


# Функция для получения данных с Центрального банка России
# ЦБ РФ отдаёт курс в рублях и количество единиц валюты.
def get_cbr_rates() -> list[tuple[str, str, str]]:
    url = "https://www.cbr.ru/scripts/XML_daily.asp"
    response = requests.get(url, timeout=30)
    response.encoding = "windows-1251"

    root = ET.fromstring(response.text)
    data: list[tuple[str, str, str]] = []

    for valute in root.findall("Valute"):
        char_code = valute.find("CharCode").text
        nominal = valute.find("Nominal").text
        value = valute.find("Value").text.replace(",", ".")
        data.append((char_code, nominal, value))

    return data


# Функция для получения курса RUB с сайта gogo.mn
# Используем для RUB, так как он нужен отдельно.
def get_rub_rate_and_date() -> tuple[str | None, str | None]:
    url = "https://gogo.mn/exchange"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text("\n", strip=True)

    match = re.search(
        r"RUB\s+ОХУ-ын рубль\s+Сүүлд шинэчлэгдсэн огноо:\s*(\d{4}/\d{2}/\d{2})\s+([\d,]+(?:\.\d+)?)",
        text,
    )

    if match:
        date = match.group(1)
        rate = match.group(2)
        return rate, date

    return None, None


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

def cleanup_old_history(current_dt) -> None:
    cutoff_date = current_dt.date() - timedelta(days=6)

    for history_file in HISTORY_DIR.glob("*.json"):
        try:
            file_date = datetime.strptime(history_file.stem, "%Y-%m-%d").date()
            if file_date < cutoff_date:
                history_file.unlink()
        except Exception:
            continue


def normalize_rate(value: str | None) -> str:
    if not value:
        return "—"
    return value.strip()


def build_rows(
    currency_data: list[list[str]],
    cbr_rates: list[tuple[str, str, str]],
    rub_rate: str | None,
) -> list[dict[str, str]]:
    capitron_lookup = {
        row[0]: {
            "mon_rate": normalize_rate(row[1]),
            "cap_rate": normalize_rate(row[2]),
        }
        for row in currency_data
    }

    cbr_lookup = {}
    for code, nominal, rate in cbr_rates:
        try:
            nominal_value = Decimal(str(nominal).replace(",", "."))
            rate_value = Decimal(str(rate).replace(",", "."))
            rate_per_unit = rate_value / nominal_value

            cbr_lookup[code] = format(rate_per_unit, "f")
        except Exception:
            cbr_lookup[code] = "—"

    rows: list[dict[str, str]] = []
    for code in TRACKED:
        mon_value = "—"
        cap_value = "—"
        cbr_rate = "—"

        if code in capitron_lookup:
            mon_value = capitron_lookup[code]["mon_rate"]
            cap_value = capitron_lookup[code]["cap_rate"]

        if code == "MNT":
            mon_value = "1.00"
            cap_value = "1.00"

        if code == "RUB" and rub_rate:
            mon_value = normalize_rate(rub_rate)
            cap_value = normalize_rate(rub_rate)
            cbr_rate = "1.0000"

        if code in cbr_lookup:
            cbr_rate = cbr_lookup[code]

        rows.append(
            {
                "code": code,
                "name": CURRENCY_NAMES.get(code, code),
                "mongol_bank_mnt": mon_value,
                "capitron_mnt": cap_value,
                "cbr_rate_rub": cbr_rate,
            }
        )

    return rows


# Функция для сохранения данных в txt-файл — логика сохранена по смыслу из пользовательского кода.
def save_snapshot_txt(
    filename: Path,
    currency_data: list[list[str]],
    cbr_rates: list[tuple[str, str, str]],
    rate: str | None,
    date: str | None,
) -> None:
    with filename.open("w", encoding="utf-8") as f:
        f.write("Данные о курсах валют с сайта Capitron Bank:\n")
        f.write("---------------------------------------------------\n")
        f.write(f"{'Валюта':<10}{'Курс монгольского банка':<25}{'Курс продажи (внешний рынок)':<35}\n")
        f.write("-" * 80 + "\n")
        for row in currency_data:
            f.write(f"{row[0]:<10}{row[1]:<25}{row[2]:<35}\n")

        f.write("\n\n")

        f.write("Данные о курсах валют с Центрального банка России:\n")
        f.write("-----------------------------------------------------\n")
        f.write(f"{'CODE':<10}{'UNITS':<10}{'RATE':<10}\n")
        f.write("-" * 30 + "\n")
        for row in cbr_rates:
            f.write(f"{row[0]:<10}{row[1]:<10}{row[2]:<10}\n")

        f.write("\n\n")

        f.write("Данные о курсе рубля, полученные с сайта gogo.mn:\n")
        f.write("---------------------------------------------------\n")
        if rate and date:
            f.write(f"RUB: {rate}\n")
            f.write(f"Date: {date}\n")
        else:
            f.write("Курс RUB не найден.\n")


# Основная функция, которая вызывает все остальные и сохраняет всё в json + txt.
def main() -> None:
    ensure_dirs()

    current_dt = datetime.now(ZoneInfo("Asia/Vladivostok"))
    current_date = current_dt.strftime("%Y-%m-%d")
    snapshot_path = SNAPSHOT_DIR / f"currency_data_{current_date}.txt"

    currency_data = get_currency_data()
    cbr_rates = get_cbr_rates()
    rub_rate, rub_date = get_rub_rate_and_date()

    rows = build_rows(currency_data, cbr_rates, rub_rate)

    payload = {
        "updated_at_vladivostok": current_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "date": current_dt.strftime("%Y-%m-%d"),
        "rub_source_date": rub_date or "—",
        "rows": rows,
    }

    with JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    history_file = HISTORY_DIR / f"{current_dt.strftime('%Y-%m-%d')}.json"
    with history_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    cleanup_old_history(current_dt)

    save_snapshot_txt(snapshot_path, currency_data, cbr_rates, rub_rate, rub_date)
    print(f"Данные сохранены в {JSON_PATH}")
    print(f"TXT-снимок сохранён в {snapshot_path}")


if __name__ == "__main__":
    main()
