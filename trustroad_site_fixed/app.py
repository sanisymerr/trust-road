from __future__ import annotations

import json
import os
import re
import secrets
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "latest_rates.json"
HISTORY_DIR = BASE_DIR / "data" / "history"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VLADIVOSTOK_OFFSET = timedelta(hours=10)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "trustroad-local-dev-key")


# ---------- helpers ----------
def now_vladivostok() -> datetime:
    return datetime.utcnow() + VLADIVOSTOK_OFFSET


def parse_date(value: str | None) -> datetime | None:
    if not value or not DATE_RE.fullmatch(value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_rates() -> dict:
    payload = load_json(DATA_PATH)
    if payload:
        return payload
    return {
        "updated_at_vladivostok": "—",
        "date": None,
        "rub_source_date": "—",
        "cbr_source_date": "—",
        "rows": [],
        "source_dates": {},
    }


def load_available_dates() -> list[str]:
    if not HISTORY_DIR.exists():
        return []

    valid_dates: list[str] = []
    for file in HISTORY_DIR.glob("*.json"):
        if DATE_RE.fullmatch(file.stem):
            valid_dates.append(file.stem)

    valid_dates.sort(reverse=True)
    return valid_dates


def load_history_by_date(selected_date: str | None) -> dict | None:
    if not selected_date:
        return None

    if not DATE_RE.fullmatch(selected_date):
        return None

    history_file = (HISTORY_DIR / f"{selected_date}.json").resolve()
    history_root = HISTORY_DIR.resolve()

    if history_root not in history_file.parents:
        return None

    return load_json(history_file)


def keep_display_dates(available_dates: list[str], latest_payload: dict) -> list[str]:
    available_set = set(available_dates)
    latest_date = latest_payload.get("date") or (available_dates[0] if available_dates else None)
    if not latest_date:
        return []

    display_dates = [latest_date]
    latest_dt = parse_date(latest_date)
    if latest_dt:
        previous_candidate = (latest_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        if previous_candidate in available_set:
            display_dates.append(previous_candidate)

    return display_dates


def normalize_selected_date(requested_date: str | None, display_dates: list[str], latest_payload: dict) -> str | None:
    if requested_date in display_dates:
        return requested_date

    if latest_payload.get("date") in display_dates:
        return latest_payload.get("date")

    return display_dates[0] if display_dates else None


def format_relative_label(value: str, base_date: datetime) -> str:
    dt = parse_date(value)
    if not dt:
        return value

    today = base_date.date()
    target = dt.date()

    if target == today:
        return "Сегодня"
    if target == today - timedelta(days=1):
        return "Вчера"
    return dt.strftime("%d.%m")


def format_human_date(value: str | None) -> str:
    dt = parse_date(value)
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y")


def build_date_options(display_dates: list[str], selected_date: str | None) -> list[dict]:
    base = now_vladivostok()
    options = []
    for value in display_dates:
        options.append(
            {
                "value": value,
                "label": format_relative_label(value, base),
                "date_text": format_human_date(value),
                "is_selected": value == selected_date,
                "href": url_for("index", date=value),
            }
        )
    return options


def parse_rate(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(" ", "").replace(",", ""))
    except ValueError:
        return None


def format_delta_value(value: float) -> str:
    text = f"{abs(value):.6f}".rstrip("0").rstrip(".")
    return text or "0"


def make_delta(current_value: str | None, previous_value: str | None, unit: str) -> dict | None:
    current_num = parse_rate(current_value)
    previous_num = parse_rate(previous_value)

    if current_num is None or previous_num is None:
        return None

    diff = current_num - previous_num
    if abs(diff) < 1e-12:
        return {"kind": "flat", "text": "без изменений"}

    return {
        "kind": "up" if diff > 0 else "down",
        "text": f"{'↑' if diff > 0 else '↓'} на {format_delta_value(diff)} {unit}",
    }


def enrich_rows_with_deltas(current_rows: list[dict], previous_rows: list[dict], show_changes: bool) -> list[dict]:
    previous_map = {row.get("code"): row for row in previous_rows}
    enriched: list[dict] = []

    for row in current_rows:
        item = dict(row)
        previous_row = previous_map.get(row.get("code"), {})

        item["delta_mongol"] = make_delta(row.get("mongol_bank_mnt"), previous_row.get("mongol_bank_mnt"), "MNT") if show_changes else None
        item["delta_capitron"] = make_delta(row.get("capitron_mnt"), previous_row.get("capitron_mnt"), "MNT") if show_changes else None
        item["delta_cbr"] = make_delta(row.get("cbr_rate_rub"), previous_row.get("cbr_rate_rub"), "RUB") if show_changes else None
        enriched.append(item)

    return enriched


def get_csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_hex(16)
        session["csrf_token"] = token
    return token


def run_update() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "update_data.py")],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=300,
            check=True,
        )
        message = result.stdout.strip() or "Данные успешно обновлены."
        return True, message
    except subprocess.CalledProcessError as exc:
        error_text = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        return False, error_text
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


# ---------- security headers ----------
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


# ---------- routes ----------
@app.route("/", methods=["GET"])
def index():
    latest_payload = load_rates()
    available_dates = load_available_dates()
    display_dates = keep_display_dates(available_dates, latest_payload)
    requested_date = request.args.get("date")
    selected_date = normalize_selected_date(requested_date, display_dates, latest_payload)

    selected_payload = latest_payload if selected_date == latest_payload.get("date") else load_history_by_date(selected_date)
    if not selected_payload:
        selected_payload = latest_payload
        selected_date = latest_payload.get("date")

    previous_date = display_dates[1] if len(display_dates) > 1 else None
    show_changes = bool(selected_date and display_dates and selected_date == display_dates[0] and previous_date)
    previous_payload = load_history_by_date(previous_date) if previous_date else None

    data = dict(selected_payload)
    data["rows"] = enrich_rows_with_deltas(
        selected_payload.get("rows", []),
        previous_payload.get("rows", []) if previous_payload else [],
        show_changes,
    )

    rows = data.get("rows", [])
    stats = {
        "currencies_count": len(rows),
        "selected_date": format_human_date(selected_date),
        "updated_at": data.get("updated_at_vladivostok", "—"),
        "show_changes": show_changes,
    }

    return render_template(
        "index.html",
        data=data,
        selected_date=selected_date,
        selected_date_label=format_relative_label(selected_date, now_vladivostok()) if selected_date else "—",
        date_options=build_date_options(display_dates, selected_date),
        show_changes=show_changes,
        previous_date=previous_date,
        previous_date_text=format_human_date(previous_date) if previous_date else None,
        csrf_token=get_csrf_token(),
        stats=stats,
    )


@app.route("/refresh", methods=["POST"])
def refresh():
    form_token = request.form.get("csrf_token", "")
    if not secrets.compare_digest(form_token, session.get("csrf_token", "")):
        abort(400, description="Неверный токен формы")

    ok, message = run_update()
    flash("Курсы успешно обновлены." if ok else f"Не удалось обновить курсы: {message}", "success" if ok else "error")
    return redirect(url_for("index"))


@app.route("/health", methods=["GET"])
def health():
    payload = load_rates()
    return jsonify(
        {
            "ok": True,
            "latest_date": payload.get("date"),
            "updated_at_vladivostok": payload.get("updated_at_vladivostok"),
            "history_dates": load_available_dates(),
        }
    )


@app.route("/api/rates", methods=["GET"])
def api_rates():
    return jsonify(load_rates())


@app.route("/api/latest.json", methods=["GET"])
def api_latest():
    return jsonify(load_rates())


@app.route("/api/dates", methods=["GET"])
def api_dates():
    payload = load_rates()
    available_dates = load_available_dates()
    return jsonify(
        {
            "dates": keep_display_dates(available_dates, payload),
            "latest_date": payload.get("date"),
        }
    )


@app.route("/api/history/<selected_date>", methods=["GET"])
def api_history(selected_date: str):
    if not DATE_RE.fullmatch(selected_date):
        return jsonify({"error": "Неверный формат даты. Используй YYYY-MM-DD"}), 400

    payload = load_history_by_date(selected_date)
    if payload is None:
        return jsonify({"error": "Дата не найдена"}), 404

    return jsonify(payload)


@app.route("/api/history/<selected_date>.json", methods=["GET"])
def api_history_json(selected_date: str):
    return api_history(selected_date)


@app.route("/download/latest", methods=["GET"])
def download_latest():
    if not DATA_PATH.exists():
        return jsonify({"error": "Файл latest_rates.json не найден"}), 404

    return send_file(
        DATA_PATH,
        mimetype="application/json",
        as_attachment=True,
        download_name="latest_rates.json",
    )


@app.route("/download/history/<selected_date>", methods=["GET"])
def download_history(selected_date: str):
    if not DATE_RE.fullmatch(selected_date):
        return jsonify({"error": "Неверный формат даты. Используй YYYY-MM-DD"}), 400

    history_file = HISTORY_DIR / f"{selected_date}.json"
    if not history_file.exists():
        return jsonify({"error": "Дата не найдена"}), 404

    return send_file(
        history_file,
        mimetype="application/json",
        as_attachment=True,
        download_name=f"{selected_date}.json",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
