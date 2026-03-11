from __future__ import annotations
import re
import json
import os
import subprocess
import sys
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, flash, redirect, render_template, request, url_for
from datetime import datetime, timedelta
import calendar

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
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("SECRET_KEY не задан")

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
    return dates


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

def normalize_month_cursor(month_cursor: str | None, selected_date: str | None, available_dates: list[str]) -> str:
    base = selected_date or (available_dates[0] if available_dates else datetime.now().strftime("%Y-%m-%d"))

    try:
        if month_cursor:
            dt = datetime.strptime(month_cursor, "%Y-%m")
            return dt.strftime("%Y-%m")
    except Exception:
        pass

    try:
        dt = datetime.strptime(base, "%Y-%m-%d")
        return dt.strftime("%Y-%m")
    except Exception:
        return datetime.now().strftime("%Y-%m")


def build_calendar_days(month_cursor: str, available_dates: list[str], selected_date: str | None) -> list[dict]:
    available_set = set(available_dates)
    current = datetime.strptime(month_cursor, "%Y-%m")
    cal = calendar.Calendar(firstweekday=0)
    days = []

    for week in cal.monthdatescalendar(current.year, current.month):
        for day in week:
            value = day.strftime("%Y-%m-%d")
            in_current_month = day.month == current.month

            days.append({
                "value": value,
                "day": f"{day.day:02d}" if in_current_month else "",
                "weekday": RU_WEEKDAYS_SHORT[day.weekday()] if in_current_month else "",
                "is_current_month": in_current_month,
                "is_available": in_current_month and value in available_set,
                "is_selected": value == selected_date,
            })

    return days


def get_calendar_title(month_cursor: str) -> str:
    dt = datetime.strptime(month_cursor, "%Y-%m")
    return f"{RU_MONTHS[dt.month - 1]} {dt.year}"


def get_prev_month(month_cursor: str) -> str:
    dt = datetime.strptime(month_cursor, "%Y-%m")
    prev_dt = (dt.replace(day=1) - timedelta(days=1)).replace(day=1)
    return prev_dt.strftime("%Y-%m")


def get_next_month(month_cursor: str) -> str:
    dt = datetime.strptime(month_cursor, "%Y-%m")
    next_dt = (dt.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_dt.strftime("%Y-%m")


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

def run_archive_update() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "update_data.py"), "--save-history"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=240,
            check=True,
        )
        message = result.stdout.strip() or "Архив успешно сохранён."
        return True, message
    except subprocess.CalledProcessError as exc:
        error_text = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        return False, error_text
    except Exception as exc:
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
    month_param = request.args.get("month")
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

    month_cursor = normalize_month_cursor(month_param, selected_date, available_dates)
    calendar_days = build_calendar_days(month_cursor, available_dates, selected_date)

    return render_template(
        "index.html",
        data=data,
        available_dates=available_dates,
        selected_date=selected_date,
        month_title=get_calendar_title(month_cursor),
        calendar_days=calendar_days,
        month_cursor=month_cursor,
        prev_month=get_prev_month(month_cursor),
        next_month=get_next_month(month_cursor),
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
        minute="0,30",
        id="half_hour_rates_update",
        replace_existing=True,
    )
    scheduler.start()

    scheduler.add_job(
        func=run_archive_update,
        trigger="cron",
        hour=23,
        minute=59,
        id="daily_history_snapshot",
        replace_existing=True,
    )


def ensure_initial_data() -> None:
    run_update()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
