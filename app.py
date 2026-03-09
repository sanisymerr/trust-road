from __future__ import annotations
import re
import json
import os
import subprocess
import sys
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, flash, redirect, render_template, request, url_for
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "latest_rates.json"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HISTORY_DIR = BASE_DIR / "data" / "history"
DEFAULT_PORT = 5000
RU_MONTHS = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]

RU_WEEKDAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

app = Flask(__name__)
app.secret_key = "trustroad-secret-key"

scheduler = BackgroundScheduler(timezone="Asia/Vladivostok")


def load_rates() -> dict:
    if not DATA_PATH.exists():
        return {
            "updated_at_vladivostok": "—",
            "rub_source_date": "—",
            "rows": [],
        }

    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_available_dates() -> list[str]:
    history_dir = BASE_DIR / "data" / "history"
    if not history_dir.exists():
        return []

    dates = []
    for file in history_dir.glob("*.json"):
        dates.append(file.stem)

    dates.sort(reverse=True)
    return dates[:7]


def load_rates_by_date(selected_date: str | None) -> dict:
    if selected_date and DATE_RE.fullmatch(selected_date):
        history_file = (BASE_DIR / "data" / "history" / f"{selected_date}.json").resolve()
        history_root = (BASE_DIR / "data" / "history").resolve()

        if history_root in history_file.parents and history_file.exists():
            with history_file.open("r", encoding="utf-8") as f:
                return json.load(f)

    return load_rates()


def build_date_items(dates: list[str]) -> list[dict]:
    items = []
    for value in dates:
        try:
            dt = datetime.strptime(value, "%Y-%m-%d")
            items.append({
                "value": value,
                "day": f"{dt.day:02d}",
                "weekday": RU_WEEKDAYS_SHORT[dt.weekday()],
            })
        except Exception:
            items.append({
                "value": value,
                "day": value[-2:],
                "weekday": "",
            })
    return items


def get_month_title(selected_date: str | None, available_dates: list[str]) -> str:
    base_date = selected_date or (available_dates[0] if available_dates else None)
    if not base_date:
        return "Последние 7 дней"

    try:
        dt = datetime.strptime(base_date, "%Y-%m-%d")
        return f"{RU_MONTHS[dt.month - 1]} {dt.year}"
    except Exception:
        return "Последние 7 дней"


def run_update() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "update_data.py")],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=240,
            check=True,
        )
        message = result.stdout.strip() or "Данные успешно обновлены."
        return True, message
    except subprocess.CalledProcessError as exc:
        error_text = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        return False, error_text
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)

def parse_rate(value):
    if value is None:
        return None
    try:
        return float(str(value).replace(" ", "").replace(",", ""))
    except Exception:
        return None

def format_delta_value(value: float) -> str:
    text = f"{abs(value):.6f}".rstrip("0").rstrip(".")
    return text or "0"

def make_delta(current_value, previous_value, unit: str):
    current_num = parse_rate(current_value)
    previous_num = parse_rate(previous_value)

    if current_num is None or previous_num is None:
        return None

    diff = current_num - previous_num

    if abs(diff) < 1e-12:
        return {
            "kind": "flat",
            "text": "без изменений"
        }

    return {
        "kind": "up" if diff > 0 else "down",
        "text": f"{'↑' if diff > 0 else '↓'} на {format_delta_value(diff)} {unit}"
    }

@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    return response

def enrich_rows_with_deltas(current_rows, previous_rows, show_changes: bool):
    if not show_changes:
        enriched = []
        for row in current_rows:
            item = dict(row)
            item["delta_mongol"] = None
            item["delta_capitron"] = None
            item["delta_cbr"] = None
            enriched.append(item)
        return enriched

    previous_map = {row.get("code"): row for row in previous_rows}
    enriched = []

    for row in current_rows:
        item = dict(row)
        prev_row = previous_map.get(row.get("code"), {})

        item["delta_mongol"] = make_delta(
            row.get("mongol_bank_mnt"),
            prev_row.get("mongol_bank_mnt"),
            "MNT"
        )
        item["delta_capitron"] = make_delta(
            row.get("capitron_mnt"),
            prev_row.get("capitron_mnt"),
            "MNT"
        )
        item["delta_cbr"] = make_delta(
            row.get("cbr_rate_rub"),
            prev_row.get("cbr_rate_rub"),
            "RUB"
        )

        enriched.append(item)

    return enriched

@app.route("/", methods=["GET"])
def index():
    requested_date = request.args.get("date")
    available_dates = load_available_dates()

    latest_date = available_dates[0] if available_dates else None
    selected_date = requested_date or latest_date

    data = load_rates_by_date(selected_date)

    show_changes = bool(
        selected_date
        and latest_date
        and selected_date == latest_date
        and len(available_dates) > 1
    )

    previous_date = available_dates[1] if show_changes else None
    previous_data = load_rates_by_date(previous_date) if previous_date else {"rows": []}

    data["rows"] = enrich_rows_with_deltas(
        data.get("rows", []),
        previous_data.get("rows", []),
        show_changes
    )

    return render_template(
        "index.html",
        data=data,
        available_dates=available_dates,
        selected_date=selected_date,
        date_items=build_date_items(available_dates),
        month_title=get_month_title(selected_date, available_dates),
        show_changes=show_changes,
        previous_date=previous_date,
    )


@app.route("/refresh", methods=["POST"])
def refresh():
    ok, message = run_update()
    if ok:
        flash("Курсы успешно обновлены.", "success")
    else:
        flash(f"Не удалось обновить курсы: {message}", "error")
    return redirect(url_for("index"))


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        func=run_update,
        trigger="cron",
        hour=12,
        minute=0,
        id="daily_rates_update",
        replace_existing=True,
    )
    scheduler.start()


def ensure_initial_data() -> None:
    if DATA_PATH.exists():
        return
    run_update()


if __name__ == "__main__":
    start_scheduler()
    ensure_initial_data()
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", DEFAULT_PORT)), debug=False)
