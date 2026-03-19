from __future__ import annotations

import json
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, getcontext
from pathlib import Path
from tempfile import NamedTemporaryFile
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

getcontext().prec = 50

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
HISTORY_DIR = DATA_DIR / "history"
JSON_PATH = DATA_DIR / "latest_rates.json"
LOG_PATH = DATA_DIR / "update.log"

TIMEZONE = ZoneInfo("Asia/Vladivostok")
CAPITRON_URL = "https://www.capitronbank.mn/p/exchange?lang=&type="
CBR_URL = "https://www.cbr.ru/scripts/XML_daily.asp"
GOGO_URL = "https://gogo.mn/exchange"

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

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (TrustRoad rates updater)"})


def setup_logging() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


logger = logging.getLogger(__name__)


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf-8") as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        temp_path = Path(tmp.name)
    temp_path.replace(path)


def load_existing_latest() -> dict | None:
    if not JSON_PATH.exists():
        return None
    with JSON_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def normalize_numeric_string(value: str | None) -> str:
    if not value:
        return "—"
    text = str(value).strip().replace("\xa0", " ")
    text = text.replace("₮", "").replace("₽", "")
    text = re.sub(r"\s+", "", text)
    text = text.replace(",", "")
    return text or "—"


def format_decimal_string(value: str | Decimal | None, digits: int = 6) -> str:
    if value is None:
        return "—"
    try:
        decimal_value = Decimal(str(value).replace(",", "."))
    except InvalidOperation:
        return "—"

    quantized = decimal_value.quantize(Decimal("1." + "0" * digits))
    text = format(quantized.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def requests_get(url: str, timeout: int = 30) -> requests.Response:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response


def extract_numeric_columns(cells: list[str]) -> list[str]:
    numeric = []
    for cell in cells:
        clean = normalize_numeric_string(cell)
        if clean != "—" and re.fullmatch(r"\d+(?:\.\d+)?", clean):
            numeric.append(clean)
    return numeric


def normalize_header_text(value: str | None) -> str:
    if not value:
        return ""
    text = value.lower().replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_visible_capitron_tables(page) -> list[dict]:
    script = r"""
    () => {
      function buildHeaders(table) {
        const headRows = Array.from(table.querySelectorAll('thead tr'));
        if (!headRows.length) return [];
        const matrix = [];
        let maxCols = 0;

        headRows.forEach((row, rowIndex) => {
          matrix[rowIndex] = matrix[rowIndex] || [];
          let colIndex = 0;
          Array.from(row.children).forEach((cell) => {
            while (matrix[rowIndex][colIndex]) colIndex += 1;
            const text = (cell.innerText || cell.textContent || '').replace(/\s+/g, ' ').trim();
            const colspan = Math.max(parseInt(cell.getAttribute('colspan') || '1', 10), 1);
            const rowspan = Math.max(parseInt(cell.getAttribute('rowspan') || '1', 10), 1);
            for (let r = 0; r < rowspan; r += 1) {
              matrix[rowIndex + r] = matrix[rowIndex + r] || [];
              for (let c = 0; c < colspan; c += 1) {
                matrix[rowIndex + r][colIndex + c] = text;
              }
            }
            colIndex += colspan;
            if (colIndex > maxCols) maxCols = colIndex;
          });
        });

        const headers = [];
        for (let col = 0; col < maxCols; col += 1) {
          const parts = [];
          for (let row = 0; row < matrix.length; row += 1) {
            const value = (matrix[row] && matrix[row][col]) ? matrix[row][col].trim() : '';
            if (value && !parts.includes(value)) parts.push(value);
          }
          headers.push(parts.join(' | '));
        }
        return headers;
      }

      function getTableDate(table) {
        const candidates = [];
        const headerTexts = Array.from(table.querySelectorAll('thead th, thead td')).map((el) => (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim());
        candidates.push(...headerTexts);
        const topText = (table.innerText || '').slice(0, 300);
        candidates.push(topText);
        const raw = candidates.join(' ');
        const match = raw.match(/\b(\d{4}[./-]\d{2}[./-]\d{2})\b/);
        return match ? match[1] : '';
      }

      return Array.from(document.querySelectorAll('table')).map((table) => {
        const style = window.getComputedStyle(table);
        const rect = table.getBoundingClientRect();
        const visible = style.display !== 'none' && style.visibility !== 'hidden' && !!table.offsetParent && rect.width > 0 && rect.height > 0;
        const headers = buildHeaders(table);
        const bodyRows = Array.from(table.querySelectorAll('tbody tr')).map((row) => (
          Array.from(row.querySelectorAll('td, th')).map((cell) => (cell.innerText || cell.textContent || '').replace(/\s+/g, ' ').trim())
        )).filter((row) => row.some(Boolean));
        return { visible, headers, rows: bodyRows, table_date: getTableDate(table), text_sample: (table.innerText || '').slice(0, 500) };
      }).filter((table) => table.visible && table.rows.length);
    }
    """
    return page.evaluate(script)

def choose_capitron_columns(headers: list[str]) -> tuple[int | None, int | None, int | None]:
    official_idx = None
    noncash_sell_idx = None
    code_idx = 0 if headers else None

    for idx, header in enumerate(headers):
        normalized = normalize_header_text(header)
        if official_idx is None and (
            'албан ханш' in normalized
            or 'official' in normalized
            or ('mongol bank' in normalized and 'currency' not in normalized and 'name' not in normalized)
        ):
            official_idx = idx

        if noncash_sell_idx is None:
            is_noncash_sell = (
                ('бэлэн бус' in normalized and 'зарах' in normalized)
                or ('non cash' in normalized and 'sell' in normalized)
                or ('innoncash' in normalized and 'sell' in normalized)
                or ('noncash' in normalized and 'sell' in normalized)
            )
            if is_noncash_sell:
                noncash_sell_idx = idx

        if code_idx == 0 and ('currency name' in normalized or 'валютын нэр' in normalized):
            code_idx = 0

    return code_idx, official_idx, noncash_sell_idx


def row_to_capitron_values(cells: list[str], official_idx: int | None, noncash_sell_idx: int | None) -> tuple[str | None, str | None, str | None]:
    code = (cells[0] if cells else '').strip().upper()
    if not re.fullmatch(r'[A-Z]{3}', code) or code in {'ZAU', 'ZAG'}:
        return None, None, None

    official_value = None
    noncash_sell_value = None

    if official_idx is not None and official_idx < len(cells):
        clean = normalize_numeric_string(cells[official_idx])
        if clean != '—' and re.fullmatch(r'\d+(?:\.\d+)?', clean):
            official_value = clean

    if noncash_sell_idx is not None and noncash_sell_idx < len(cells):
        clean = normalize_numeric_string(cells[noncash_sell_idx])
        if clean != '—' and re.fullmatch(r'\d+(?:\.\d+)?', clean):
            noncash_sell_value = clean

    if official_value and noncash_sell_value:
        return code, official_value, noncash_sell_value

    numeric = extract_numeric_columns(cells[1:])
    if len(numeric) >= 5:
        return code, numeric[0], numeric[4]
    if len(numeric) >= 2:
        return code, numeric[0], numeric[-1]
    return code, official_value, noncash_sell_value


def normalize_table_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(\d{4}[./-]\d{2}[./-]\d{2})", value)
    if not match:
        return None
    normalized = match.group(1).replace('/', '-').replace('.', '-')
    return normalized if re.fullmatch(r'\d{4}-\d{2}-\d{2}', normalized) else None


def extract_capitron_page_date(page) -> str | None:
    body_text = page.locator('body').inner_text(timeout=10000)
    matches = re.findall(r'\b(\d{4}[./-]\d{2}[./-]\d{2})\b', body_text)
    for raw in matches:
        normalized = normalize_table_date(raw)
        if normalized:
            return normalized
    return None


def extract_capitron_candidates(page) -> list[dict]:
    page.wait_for_selector('table', timeout=60000)
    page.wait_for_timeout(1500)
    tables = get_visible_capitron_tables(page)

    candidates: list[dict] = []
    for table in tables:
        headers = table.get('headers', [])
        rows = table.get('rows', [])
        table_date = normalize_table_date(table.get('table_date'))
        _code_idx, official_idx, noncash_sell_idx = choose_capitron_columns(headers)
        extracted: list[list[str]] = []

        for cells in rows:
            code, mongol_value, capitron_value = row_to_capitron_values(cells, official_idx, noncash_sell_idx)
            if not code or not mongol_value or not capitron_value:
                continue
            extracted.append([code, mongol_value, capitron_value])

        codes = {row[0] for row in extracted}
        score = len(codes.intersection({'USD', 'EUR', 'CNY', 'JPY', 'KRW', 'GBP', 'CHF', 'SGD', 'HKD'}))
        if official_idx is not None:
            score += 2
        if noncash_sell_idx is not None:
            score += 4
        if table_date:
            score += 2

        if extracted:
            candidates.append(
                {
                    'rows': extracted,
                    'score': score,
                    'table_date': table_date,
                    'headers': headers,
                }
            )

    candidates.sort(key=lambda item: item['score'], reverse=True)
    return candidates


def choose_capitron_candidate(candidates: list[dict], current_date: str) -> dict | None:
    for candidate in candidates:
        if candidate.get('table_date') == current_date:
            return candidate
    return candidates[0] if candidates else None


def force_capitron_date(page, target_date: str) -> None:
    page.evaluate(
        r"""
        (targetDate) => {
          const slashDate = targetDate.replace(/-/g, '/');
          const dotDate = targetDate.replace(/-/g, '.');
          const trigger = (el, type) => el.dispatchEvent(new Event(type, { bubbles: true }));

          const inputs = Array.from(document.querySelectorAll('input'));
          for (const input of inputs) {
            const type = (input.getAttribute('type') || '').toLowerCase();
            const value = (input.value || '').trim();
            const placeholder = (input.getAttribute('placeholder') || '').trim();
            const looksLikeDate = type === 'date' || /\d{4}[-./]\d{2}[-./]\d{2}/.test(value) || /\d{4}[-./]\d{2}[-./]\d{2}/.test(placeholder);
            if (!looksLikeDate) continue;
            input.focus();
            input.value = targetDate;
            trigger(input, 'input');
            trigger(input, 'change');
            trigger(input, 'blur');
          }

          const clickable = Array.from(document.querySelectorAll('button, [role="button"], .flatpickr-day, .datepicker-day, .calendar-day, .dp-day'));
          for (const el of clickable) {
            const text = (el.innerText || el.textContent || '').replace(/\s+/g, ' ').trim();
            if (!text) continue;
            if (text === targetDate || text === slashDate || text === dotDate) {
              el.click();
            }
          }
        }
        """,
        target_date,
    )


def wait_for_capitron_fresh_rows(page, current_date: str, previous_payload: dict | None) -> tuple[list[list[str]], str | None]:
    last_rows: list[list[str]] = []
    stable_hits = 0
    last_error: Exception | None = None

    for step in range(12):
        try:
            candidates = extract_capitron_candidates(page)
            candidate = choose_capitron_candidate(candidates, current_date)
            if not candidate:
                raise RuntimeError('Capitron не отдал ни одной подходящей таблицы')

            rows = candidate.get('rows', [])
            table_date = candidate.get('table_date') or extract_capitron_page_date(page)

            if table_date and table_date != current_date:
                force_capitron_date(page, current_date)
                raise RuntimeError(f'Capitron показал дату {table_date} вместо {current_date}')

            if not validate_capitron_rows(rows):
                raise RuntimeError('Таблица Capitron загружена неполностью')

            if is_suspiciously_stale_capitron(rows, previous_payload, current_date):
                force_capitron_date(page, current_date)
                raise RuntimeError('Capitron отдал подозрительно вчерашние значения')

            if rows == last_rows:
                stable_hits += 1
            else:
                stable_hits = 0
                last_rows = rows

            if stable_hits >= 1 or step >= 8:
                return rows, table_date
        except (PlaywrightTimeoutError, RuntimeError) as exc:
            last_error = exc
            logger.warning('Capitron wait step %s failed: %s', step + 1, exc)

        page.wait_for_timeout(1500)

    raise RuntimeError(f'Не удалось дождаться свежей таблицы Capitron: {last_error}')


def validate_capitron_rows(rows: list[list[str]]) -> bool:
    codes = {row[0] for row in rows}
    required = {"USD", "EUR", "CNY", "JPY", "KRW", "GBP", "CHF", "SGD", "HKD"}
    return required.issubset(codes)


def build_capitron_map_from_payload(payload: dict | None) -> dict[str, str]:
    if not payload:
        return {}
    mapping: dict[str, str] = {}
    for row in payload.get("rows", []):
        code = row.get("code")
        value = row.get("capitron_mnt")
        if code and value and value != "—":
            mapping[code] = normalize_numeric_string(value)
    return mapping


def build_capitron_map_from_rows(rows: list[list[str]]) -> dict[str, str]:
    return {code: normalize_numeric_string(cap_rate) for code, _mon, cap_rate in rows}


def is_suspiciously_stale_capitron(rows: list[list[str]], previous_payload: dict | None, current_date: str) -> bool:
    if not previous_payload:
        return False

    previous_date = previous_payload.get("date")
    if previous_date == current_date:
        return False

    previous_map = build_capitron_map_from_payload(previous_payload)
    current_map = build_capitron_map_from_rows(rows)
    comparable_codes = [code for code in ["USD", "EUR", "CNY", "JPY", "KRW"] if code in current_map and code in previous_map]

    if len(comparable_codes) < 4:
        return False

    unchanged = sum(1 for code in comparable_codes if current_map[code] == previous_map[code])
    return unchanged == len(comparable_codes)


def get_currency_data(current_date: str, previous_payload: dict | None) -> list[list[str]]:
    last_error: Exception | None = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for attempt in range(1, 5):
                context = browser.new_context(ignore_https_errors=True, locale="en-US", service_workers="block")
                context.set_default_timeout(60000)
                context.add_init_script("""() => { try { localStorage.clear(); sessionStorage.clear(); } catch (e) {} }""")
                page = context.new_page()
                page.set_extra_http_headers(
                    {
                        "Cache-Control": "no-cache, no-store, must-revalidate",
                        "Pragma": "no-cache",
                        "Expires": "0",
                    }
                )

                url = f"{CAPITRON_URL}&_ts={int(time.time() * 1000)}_{attempt}"
                logger.info("Capitron attempt %s: %s", attempt, url)

                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_load_state("networkidle", timeout=60000)
                    page.wait_for_timeout(2500 + attempt * 500)
                    force_capitron_date(page, current_date)
                    rows, page_date = wait_for_capitron_fresh_rows(page, current_date=current_date, previous_payload=previous_payload)

                    logger.info("Capitron rows received: %s (date=%s)", len(rows), page_date or '—')
                    return rows
                except (PlaywrightTimeoutError, RuntimeError) as exc:
                    last_error = exc
                    logger.warning("Capitron attempt %s failed: %s", attempt, exc)
                finally:
                    context.close()

        finally:
            browser.close()

    raise RuntimeError(f"Не удалось получить актуальные данные Capitron: {last_error}")


def get_cbr_rates() -> tuple[list[tuple[str, str, str]], str | None]:
    response = requests_get(CBR_URL)
    response.encoding = "windows-1251"
    root = ET.fromstring(response.text)

    cbr_source_date = root.attrib.get("Date")
    if cbr_source_date:
        try:
            cbr_source_date = datetime.strptime(cbr_source_date, "%d.%m.%Y").strftime("%Y-%m-%d")
        except ValueError:
            pass

    data: list[tuple[str, str, str]] = []
    for valute in root.findall("Valute"):
        char_code = (valute.findtext("CharCode") or "").strip()
        nominal = (valute.findtext("Nominal") or "").strip()
        value = (valute.findtext("Value") or "").replace(",", ".").strip()
        if char_code:
            data.append((char_code, nominal, value))

    return data, cbr_source_date


def get_rub_rate_and_date() -> tuple[str | None, str | None]:
    response = requests_get(GOGO_URL)
    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text("\n", strip=True)

    match = re.search(
        r"RUB\s+ОХУ-ын рубль\s+Сүүлд шинэчлэгдсэн огноо:\s*(\d{4}/\d{2}/\d{2})\s+([\d,]+(?:\.\d+)?)",
        text,
    )

    if not match:
        raise RuntimeError("Не удалось получить курс RUB с gogo.mn")

    rub_date = match.group(1).replace("/", "-")
    rub_rate = normalize_numeric_string(match.group(2))
    return rub_rate, rub_date


def build_rows(currency_data: list[list[str]], cbr_rates: list[tuple[str, str, str]], rub_rate: str | None) -> list[dict[str, str]]:
    capitron_lookup = {
        row[0]: {
            "mongol": format_decimal_string(row[1]),
            "capitron": format_decimal_string(row[2]),
        }
        for row in currency_data
    }

    cbr_lookup: dict[str, str] = {}
    for code, nominal, rate in cbr_rates:
        try:
            nominal_value = Decimal(str(nominal).replace(",", "."))
            rate_value = Decimal(str(rate).replace(",", "."))
            rate_per_unit = rate_value / nominal_value
            cbr_lookup[code] = format_decimal_string(rate_per_unit)
        except (InvalidOperation, ZeroDivisionError):
            cbr_lookup[code] = "—"

    rows: list[dict[str, str]] = []
    for code in TRACKED:
        mongol_value = capitron_lookup.get(code, {}).get("mongol", "—")
        capitron_value = capitron_lookup.get(code, {}).get("capitron", "—")
        cbr_value = cbr_lookup.get(code, "—")

        if code == "MNT":
            mongol_value = "1"
            capitron_value = "1"

        if code == "RUB" and rub_rate:
            mongol_value = format_decimal_string(rub_rate)
            capitron_value = format_decimal_string(rub_rate)
            cbr_value = "1"

        rows.append(
            {
                "code": code,
                "name": CURRENCY_NAMES.get(code, code),
                "mongol_bank_mnt": mongol_value,
                "capitron_mnt": capitron_value,
                "cbr_rate_rub": cbr_value,
            }
        )

    return rows


def save_snapshot_txt(filename: Path, currency_data: list[list[str]], cbr_rates: list[tuple[str, str, str]], rub_rate: str | None, rub_date: str | None) -> None:
    with filename.open("w", encoding="utf-8") as fh:
        fh.write("Данные о курсах валют\n")
        fh.write("=" * 80 + "\n\n")

        fh.write("Capitron / Монголбанк\n")
        fh.write("-" * 80 + "\n")
        fh.write(f"{'Код':<8}{'Монголбанк':<18}{'Capitron':<18}\n")
        for code, mongol, capitron in currency_data:
            fh.write(f"{code:<8}{mongol:<18}{capitron:<18}\n")

        fh.write("\nЦБ РФ\n")
        fh.write("-" * 80 + "\n")
        fh.write(f"{'Код':<8}{'Номинал':<12}{'Курс':<18}\n")
        for code, nominal, rate in cbr_rates:
            fh.write(f"{code:<8}{nominal:<12}{rate:<18}\n")

        fh.write("\nRUB / gogo.mn\n")
        fh.write("-" * 80 + "\n")
        fh.write(f"Курс RUB: {rub_rate or '—'}\n")
        fh.write(f"Дата RUB: {rub_date or '—'}\n")


def cleanup_old_history(current_dt: datetime) -> None:
    keep = {
        current_dt.strftime("%Y-%m-%d"),
        (current_dt - timedelta(days=1)).strftime("%Y-%m-%d"),
    }

    for file in HISTORY_DIR.glob("*.json"):
        if file.stem not in keep:
            logger.info("Удаляю старую историю: %s", file.name)
            file.unlink(missing_ok=True)

    for file in SNAPSHOT_DIR.glob("currency_data_*.txt"):
        match = re.search(r"(\d{4}-\d{2}-\d{2})", file.name)
        if match and match.group(1) not in keep:
            logger.info("Удаляю старый snapshot: %s", file.name)
            file.unlink(missing_ok=True)


def main() -> None:
    setup_logging()
    ensure_dirs()

    current_dt = datetime.now(TIMEZONE)
    current_date = current_dt.strftime("%Y-%m-%d")
    previous_payload = load_existing_latest()
    snapshot_path = SNAPSHOT_DIR / f"currency_data_{current_date}.txt"

    logger.info("Старт обновления курсов за %s", current_date)

    currency_data = get_currency_data(current_date=current_date, previous_payload=previous_payload)
    cbr_rates, cbr_source_date = get_cbr_rates()
    rub_rate, rub_date = get_rub_rate_and_date()

    rows = build_rows(currency_data, cbr_rates, rub_rate)

    payload = {
        "updated_at_vladivostok": current_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "date": current_date,
        "rub_source_date": rub_date or "—",
        "cbr_source_date": cbr_source_date or "—",
        "source_dates": {
            "capitron_checked_at": current_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "cbr": cbr_source_date or "—",
            "rub": rub_date or "—",
        },
        "rows": rows,
    }

    atomic_write_json(JSON_PATH, payload)
    atomic_write_json(HISTORY_DIR / f"{current_date}.json", payload)
    cleanup_old_history(current_dt)
    save_snapshot_txt(snapshot_path, currency_data, cbr_rates, rub_rate, rub_date)

    logger.info("Данные сохранены в %s", JSON_PATH)
    logger.info("История сохранена в %s", HISTORY_DIR / f"{current_date}.json")
    print(f"Данные сохранены в {JSON_PATH}")
    print(f"История сохранена в {HISTORY_DIR / f'{current_date}.json'}")


if __name__ == "__main__":
    main()
