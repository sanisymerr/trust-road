from __future__ import annotations

import os
import re
import unicodedata
from typing import Dict, List, Optional

import certifi
import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

CAPITRON_URL = "https://www.capitronbank.mn/p/exchange?lang=&type="
TIMEOUT = 20

# Common aliases found on banking sites / merged cells / duplicate codes.
CODE_ALIASES = {
    "RUR": "RUB",
    "USDT": "USD",
}

# Candidate header names for the column user needs.
TARGET_HEADER_CANDIDATES = [
    "бэлэн бус зарах",
    "бэлэнбус зарах",
    "бэлэн бус",
    "cashless sell",
    "non cash sell",
    "noncash sell",
    "sell",
]


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = value.strip().lower()
    value = re.sub(r"\s+", " ", value)
    value = value.replace("ё", "е")
    return value


def parse_number(value: str) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("\xa0", " ").replace(" ", "")
    text = text.replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def extract_currency_code(text: str) -> Optional[str]:
    raw = re.sub(r"[^A-Za-z]", "", text or "").upper()
    if len(raw) >= 6 and raw[:3] == raw[3:6]:
        raw = raw[:3]
    if len(raw) > 3:
        found = re.findall(r"[A-Z]{3}", raw)
        if found:
            raw = found[0]
    if len(raw) != 3:
        return None
    return CODE_ALIASES.get(raw, raw)


def pick_target_column(headers: List[str]) -> int:
    normalized = [normalize_text(h) for h in headers]

    # Strong matches first.
    for candidate in TARGET_HEADER_CANDIDATES:
        for i, header in enumerate(normalized):
            if candidate in header:
                return i

    # If there's a grouped header layout, choose the last numeric column as fallback.
    if len(headers) >= 3:
        return len(headers) - 1

    raise ValueError("Не удалось определить столбец 'Бэлэн бус / Зарах'.")


def fetch_html() -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        ),
        "Accept-Language": "mn,en;q=0.9,ru;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    last_error: Optional[Exception] = None

    # First, try strict certificate verification.
    try:
        response = requests.get(
            CAPITRON_URL,
            headers=headers,
            timeout=TIMEOUT,
            verify=certifi.where(),
        )
        response.raise_for_status()
        return response.text
    except Exception as exc:  # noqa: BLE001
        last_error = exc

    # Fallback for some hosts where the runtime CA bundle is broken.
    try:
        response = requests.get(
            CAPITRON_URL,
            headers=headers,
            timeout=TIMEOUT,
            verify=False,
        )
        response.raise_for_status()
        return response.text
    except Exception as exc:  # noqa: BLE001
        last_error = exc

    raise RuntimeError(f"Не удалось загрузить страницу Capitron: {last_error}")


def parse_rates_from_html(html: str) -> Dict[str, float]:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        raise ValueError("На странице Capitron не найдены таблицы с курсами.")

    best_rates: Dict[str, float] = {}
    last_error: Optional[Exception] = None

    for table in tables:
        try:
            rates = parse_rates_from_table(table)
            if len(rates) > len(best_rates):
                best_rates = rates
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue

    if best_rates:
        return best_rates

    raise ValueError(f"Не удалось распарсить курсы Capitron: {last_error}")


def parse_rates_from_table(table) -> Dict[str, float]:
    rows = table.find_all("tr")
    if not rows:
        raise ValueError("Пустая таблица")

    headers: List[str] = []
    data_rows = []

    for row in rows:
        ths = row.find_all("th")
        tds = row.find_all("td")
        cells = ths or tds
        values = [cell.get_text(" ", strip=True) for cell in cells]
        if not values:
            continue
        if ths and not data_rows:
            headers = values
            continue
        data_rows.append(values)

    if not headers and data_rows:
        # Sometimes the first row is a header but marked with <td>.
        candidate_headers = data_rows[0]
        if any(normalize_text(x) for x in candidate_headers[1:]):
            headers = candidate_headers
            data_rows = data_rows[1:]

    if not headers:
        raise ValueError("Не найдены заголовки")

    target_col = pick_target_column(headers)
    rates: Dict[str, float] = {}

    for row in data_rows:
        if len(row) < 2:
            continue
        code = None
        for cell in row[:2]:
            code = extract_currency_code(cell)
            if code:
                break
        if not code:
            merged = " ".join(row[:2])
            code = extract_currency_code(merged)
        if not code:
            continue

        value: Optional[float] = None
        if target_col < len(row):
            value = parse_number(row[target_col])

        # Fallback: choose last numeric cell in the row.
        if value is None:
            numeric_candidates = [parse_number(cell) for cell in row[1:]]
            numeric_candidates = [x for x in numeric_candidates if x is not None]
            if numeric_candidates:
                value = numeric_candidates[-1]

        if value is None:
            continue
        rates[code] = value

    if not rates:
        raise ValueError("Не найдены курсы валют")

    return rates


def get_rates() -> Dict[str, float]:
    html = fetch_html()
    rates = parse_rates_from_html(html)

    # Normalize and keep only sensible numeric values.
    cleaned = {k: float(v) for k, v in rates.items() if isinstance(v, (int, float)) and v > 0}
    if "RUB" not in cleaned:
        raise ValueError("В таблице Capitron не найден RUB. Без него нельзя посчитать итог в рублях.")
    return cleaned


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/rates")
def api_rates():
    try:
        rates = get_rates()
        items = [{"code": code, "rate": rates[code]} for code in sorted(rates.keys())]
        return jsonify({"ok": True, "items": items, "source": CAPITRON_URL})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.get("/api/convert")
def api_convert():
    amount_raw = request.args.get("amount", "")
    currency = (request.args.get("currency", "") or "").upper().strip()

    amount = parse_number(amount_raw)
    if amount is None or amount < 0:
        return jsonify({"ok": False, "error": "Некорректная сумма."}), 400
    if not currency:
        return jsonify({"ok": False, "error": "Не выбрана валюта."}), 400

    try:
        rates = get_rates()
    except Exception as exc:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(exc)}), 500

    if currency not in rates:
        return jsonify({"ok": False, "error": f"Валюта {currency} не найдена в Capitron."}), 400

    client_rate = rates[currency]
    rub_rate = rates["RUB"]
    total_mnt = amount * client_rate
    total_rub = total_mnt / rub_rate

    return jsonify(
        {
            "ok": True,
            "amount": amount,
            "currency": currency,
            "client_rate": client_rate,
            "rub_rate": rub_rate,
            "total_mnt": total_mnt,
            "total_rub": total_rub,
            "source": CAPITRON_URL,
        }
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
