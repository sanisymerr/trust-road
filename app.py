import json
import os
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

CAPITRON_URL = "https://www.capitronbank.mn/p/exchange?lang=&type="
CACHE_DIR = Path("data")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_FILE = CACHE_DIR / "capitron_rates.json"
CACHE_TTL = 60 * 10  # 10 минут

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ru,en;q=0.9,mn;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


CURRENCY_NAMES = {
    "USD": "Ам доллар",
    "EUR": "Евро",
    "CNY": "Юань",
    "JPY": "Иен",
    "KRW": "Вон",
    "GBP": "Фунт",
    "CHF": "Франк",
    "SGD": "Сингапур доллар",
    "HKD": "Гонконг доллар",
    "RUB": "Рубль",
}


def normalize_number(value):
    if value is None:
        return None
    s = str(value).strip()
    s = s.replace("\xa0", "").replace(" ", "")
    s = s.replace(",", "")
    s = s.replace("—", "").replace("-", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def load_cache():
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_cache(rates):
    payload = {
        "updated_at": int(time.time()),
        "rates": rates,
    }
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def fetch_capitron_html():
    response = requests.get(
        CAPITRON_URL,
        headers=HEADERS,
        timeout=8,
        verify=False,
    )
    response.raise_for_status()
    return response.text


def extract_currency_code(text):
    text = (text or "").strip().upper()

    known_codes = list(CURRENCY_NAMES.keys())
    for code in known_codes:
        if re.search(rf"\b{code}\b", text):
            return code
        if re.search(rf"\b{code}{code}\b", text):
            return code

    return None


def parse_from_tables(html):
    soup = BeautifulSoup(html, "html.parser")
    results = {}

    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            texts = [cell.get_text(" ", strip=True) for cell in cells]

            if len(texts) < 3:
                continue

            row_text = " | ".join(texts)
            code = extract_currency_code(row_text)
            if not code:
                continue

            # Берем все числа из строки
            numbers = []
            for t in texts:
                found = re.findall(r"\d[\d,\.]*", t)
                numbers.extend(found)

            parsed_numbers = [normalize_number(x) for x in numbers]
            parsed_numbers = [x for x in parsed_numbers if x is not None]

            # На странице Capitron обычно нужный курс — последнее число строки
            if parsed_numbers:
                rate = parsed_numbers[-1]
                if rate and rate > 0:
                    results[code] = {
                        "code": code,
                        "name": CURRENCY_NAMES.get(code, code),
                        "rate": rate,
                        "raw": texts,
                    }

    return results


def parse_from_known_lines(html):
    results = {}
    for code in CURRENCY_NAMES.keys():
        matches = re.findall(
            rf"{code}(?:{code})?.{{0,200}}?(\d[\d,\.]*).{{0,50}}?(\d[\d,\.]*).{{0,50}}?(\d[\d,\.]*).{{0,50}}?(\d[\d,\.]*).{{0,50}}?(\d[\d,\.]*)",
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )

        for match in matches:
            nums = [normalize_number(x) for x in match]
            nums = [x for x in nums if x is not None]
            if nums:
                rate = nums[-1]
                if rate and rate > 0:
                    results[code] = {
                        "code": code,
                        "name": CURRENCY_NAMES.get(code, code),
                        "rate": rate,
                        "raw": nums,
                    }
                    break

    return results


def parse_capitron(html):
    merged = {}

    for parser in [parse_from_tables, parse_from_known_lines]:
        try:
            parsed = parser(html)
            if parsed:
                merged.update(parsed)
        except Exception:
            pass

    # Оставляем только нормальные валюты
    filtered = {}
    for code, value in merged.items():
        if code in CURRENCY_NAMES:
            filtered[code] = value

    return filtered

def get_rates(force=False):
    cached = load_cache()

    if not force and cached:
        age = int(time.time()) - int(cached.get("updated_at", 0))
        if age < CACHE_TTL and cached.get("rates"):
            return cached["rates"], {
                "source": "cache",
                "updated_at": cached.get("updated_at"),
            }

    try:
        html = fetch_capitron_html()
        rates = parse_capitron(html)

        if rates and "RUB" in rates:
            save_cache(rates)
            return rates, {
                "source": "capitron_live",
                "updated_at": int(time.time()),
            }

        if cached and cached.get("rates"):
            return cached["rates"], {
                "source": "stale_cache",
                "updated_at": cached.get("updated_at"),
                "warning": "Capitron parsed incorrectly, using cache.",
            }

        return {
            "USD": {"code": "USD", "name": "Ам доллар", "rate": 3566.60},
            "EUR": {"code": "EUR", "name": "Евро", "rate": 4324.00},
            "CNY": {"code": "CNY", "name": "Юань", "rate": 523.00},
            "JPY": {"code": "JPY", "name": "Иен", "rate": 23.42},
            "KRW": {"code": "KRW", "name": "Вон", "rate": 2.53},
            "GBP": {"code": "GBP", "name": "Фунт", "rate": 4951.00},
            "CHF": {"code": "CHF", "name": "Франк", "rate": 4667.00},
            "SGD": {"code": "SGD", "name": "Сингапур доллар", "rate": 2640.00},
            "HKD": {"code": "HKD", "name": "Гонконг доллар", "rate": 458.00},
            "RUB": {"code": "RUB", "name": "Рубль", "rate": 39.00},
        }, {
            "source": "fallback",
            "updated_at": int(time.time()),
            "warning": "Capitron unavailable, using fallback values.",
        }

    except Exception as e:
        if cached and cached.get("rates"):
            return cached["rates"], {
                "source": "stale_cache",
                "updated_at": cached.get("updated_at"),
                "warning": str(e),
            }

        return {
            "USD": {"code": "USD", "name": "Ам доллар", "rate": 3566.60},
            "EUR": {"code": "EUR", "name": "Евро", "rate": 4324.00},
            "CNY": {"code": "CNY", "name": "Юань", "rate": 523.00},
            "JPY": {"code": "JPY", "name": "Иен", "rate": 23.42},
            "KRW": {"code": "KRW", "name": "Вон", "rate": 2.53},
            "GBP": {"code": "GBP", "name": "Фунт", "rate": 4951.00},
            "CHF": {"code": "CHF", "name": "Франк", "rate": 4667.00},
            "SGD": {"code": "SGD", "name": "Сингапур доллар", "rate": 2640.00},
            "HKD": {"code": "HKD", "name": "Гонконг доллар", "rate": 458.00},
            "RUB": {"code": "RUB", "name": "Рубль", "rate": 39.00},
        }, {
            "source": "fallback",
            "updated_at": int(time.time()),
            "warning": str(e),
        }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/rates")
def api_rates():
    try:
        rates, meta = get_rates(force=request.args.get("force") == "1")
        return jsonify({
            "ok": True,
            "rates": rates,
            "meta": meta,
        })
    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
            "rates": {},
            "meta": {"source": "error"},
        }), 500


@app.route("/api/convert")
def api_convert():
    amount = request.args.get("amount", type=float)
    currency = (request.args.get("currency") or "").upper()

    if not amount or amount <= 0:
        return jsonify({"ok": False, "error": "Некорректная сумма."}), 400

    if not currency:
        return jsonify({"ok": False, "error": "Не указана валюта."}), 400

    rates, meta = get_rates(force=False)

    if currency not in rates:
        return jsonify({"ok": False, "error": f"Валюта {currency} не найдена."}), 404

    if "RUB" not in rates:
        return jsonify({"ok": False, "error": "Курс RUB не найден."}), 500

    rate_to_mnt = rates[currency]["rate"]
    rub_rate = rates["RUB"]["rate"]

    total_mnt = amount * rate_to_mnt
    total_rub = total_mnt / rub_rate

    return jsonify({
        "ok": True,
        "currency": currency,
        "amount": amount,
        "rate_to_mnt": rate_to_mnt,
        "rub_rate": rub_rate,
        "total_mnt": round(total_mnt, 2),
        "total_rub": round(total_rub, 2),
        "meta": meta,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)