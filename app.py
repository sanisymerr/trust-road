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
        timeout=25,
        verify=False,
    )
    response.raise_for_status()
    return response.text


def extract_currency_code(text):
    text = (text or "").strip().upper()

    m = re.search(r"\b([A-Z]{3})\1\b", text)
    if m:
        return m.group(1)

    m = re.search(r"\b([A-Z]{3})\b", text)
    if m:
        return m.group(1)

    return None


def parse_from_tables(html):
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    results = {}

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

            numbers = [normalize_number(x) for x in texts]
            numbers = [x for x in numbers if x is not None]

            # берем последнее числовое значение в строке
            if numbers:
                rate = numbers[-1]
                if rate and rate > 0:
                    results[code] = {
                        "code": code,
                        "name": texts[1] if len(texts) > 1 else code,
                        "rate": rate,
                        "raw": texts,
                    }

    return results


def parse_from_text_blocks(html):
    results = {}
    lines = html.splitlines()

    for line in lines:
        code = extract_currency_code(line)
        if not code:
            continue

        found_numbers = re.findall(r"\d[\d,\.]*", line)
        numbers = [normalize_number(x) for x in found_numbers]
        numbers = [x for x in numbers if x is not None]

        if numbers:
            rate = numbers[-1]
            if rate and rate > 0:
                results[code] = {
                    "code": code,
                    "name": code,
                    "rate": rate,
                    "raw": found_numbers,
                }

    return results


def parse_from_script_json(html):
    results = {}

    pattern = re.compile(
        r'([A-Z]{3})(?:\1)?[^0-9]{1,120}'
        r'([0-9][0-9,\.]*)[^0-9]+'
        r'([0-9][0-9,\.]*)[^0-9]+'
        r'([0-9][0-9,\.]*)[^0-9]+'
        r'([0-9][0-9,\.]*)[^0-9]+'
        r'([0-9][0-9,\.]*)'
    )

    for match in pattern.finditer(html):
        code = match.group(1)
        nums = [normalize_number(match.group(i)) for i in range(2, 7)]
        nums = [x for x in nums if x is not None]

        if nums:
            rate = nums[-1]
            if rate and rate > 0:
                results[code] = {
                    "code": code,
                    "name": code,
                    "rate": rate,
                    "raw": nums,
                }

    return results


def parse_from_known_lines(html):
    results = {}
    currency_codes = ["USD", "EUR", "CNY", "JPY", "KRW", "GBP", "CHF", "RUB"]

    for code in currency_codes:
        matches = re.findall(
            rf"{code}(?:{code})?.{{0,120}}?(\d[\d,\.]*).{{0,40}}?(\d[\d,\.]*).{{0,40}}?(\d[\d,\.]*).{{0,40}}?(\d[\d,\.]*).{{0,40}}?(\d[\d,\.]*)",
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
                        "name": code,
                        "rate": rate,
                        "raw": nums,
                    }
                    break

    return results


def parse_capitron(html):
    merged = {}

    parsers = [
        parse_from_tables,
        parse_from_script_json,
        parse_from_known_lines,
        parse_from_text_blocks,
    ]

    for parser in parsers:
        try:
            parsed = parser(html)
            if parsed:
                merged.update(parsed)
        except Exception:
            pass

    if not merged:
        return {}

    return merged


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

        if rates:
            save_cache(rates)
            return rates, {
                "source": "capitron_live",
                "updated_at": int(time.time()),
            }

        if cached and cached.get("rates"):
            return cached["rates"], {
                "source": "stale_cache",
                "updated_at": cached.get("updated_at"),
                "warning": "Capitron live parsing failed, using cached data.",
            }

        raise RuntimeError("Не удалось получить курсы Capitron.")

    except Exception as e:
        if cached and cached.get("rates"):
            return cached["rates"], {
                "source": "stale_cache",
                "updated_at": cached.get("updated_at"),
                "warning": str(e),
            }
        raise


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