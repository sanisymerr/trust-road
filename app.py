from __future__ import annotations

import atexit
import json
import logging
import os
import re
import secrets
import subprocess
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
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
LOG_PATH = BASE_DIR / "data" / "update.log"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
VLADIVOSTOK_TZ = ZoneInfo("Asia/Vladivostok")
VLADIVOSTOK_LABEL = "Asia/Vladivostok"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "trustroad-local-dev-key")
app.config["JSON_AS_ASCII"] = False

LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

update_lock = threading.Lock()
update_state_lock = threading.Lock()
update_state = {
    "is_running": False,
    "last_status": "idle",
    "last_message": "Система готова к обновлению.",
    "last_started_at": None,
    "last_finished_at": None,
}

scheduler: BackgroundScheduler | None = None
scheduler_started = False


CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "CNY": "¥",
    "JPY": "¥",
    "KRW": "₩",
    "GBP": "£",
    "CHF": "CHF",
    "SGD": "S$",
    "HKD": "HK$",
    "MNT": "₮",
    "RUB": "₽",
}


# ---------- helpers ----------
def now_vladivostok() -> datetime:
    return datetime.now(VLADIVOSTOK_TZ)


def format_dt_for_ui(value: datetime | None) -> str:
    if not value:
        return "—"
    return value.astimezone(VLADIVOSTOK_TZ).strftime("%Y-%m-%d %H:%M:%S")


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


def format_human_date(value: str | None) -> str:
    dt = parse_date(value)
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y")


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


def load_previous_history_for_deltas(latest_date: str | None) -> dict | None:
    if not latest_date:
        return None

    latest_dt = parse_date(latest_date)
    if not latest_dt:
        return None

    previous_candidate = (latest_dt - timedelta(days=1)).strftime("%Y-%m-%d")
    history_file = HISTORY_DIR / f"{previous_candidate}.json"
    return load_json(history_file)


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


def run_update_process() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "update_data.py")],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=300,
            check=True,
        )
        if result.stdout.strip():
            logger.info("update_data.py stdout: %s", result.stdout.strip().replace("\n", " | "))
        if result.stderr.strip():
            logger.warning("update_data.py stderr: %s", result.stderr.strip().replace("\n", " | "))
        return True, "Данные успешно обновлены."
    except subprocess.CalledProcessError as exc:
        error_text = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        error_text = error_text.replace(str(BASE_DIR), "").replace("  ", " ").strip()
        return False, error_text or "Обновление завершилось с ошибкой."
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _set_update_state(**changes) -> None:
    with update_state_lock:
        update_state.update(changes)


def get_update_status_payload() -> dict:
    with update_state_lock:
        state_copy = dict(update_state)

    payload = load_rates()
    state_copy["latest_data_date"] = payload.get("date")
    state_copy["latest_updated_at_vladivostok"] = payload.get("updated_at_vladivostok")
    state_copy["last_started_at"] = format_dt_for_ui(state_copy.get("last_started_at"))
    state_copy["last_finished_at"] = format_dt_for_ui(state_copy.get("last_finished_at"))
    return state_copy


def _run_update_with_reserved_lock(trigger: str) -> None:
    started_at = now_vladivostok()
    _set_update_state(
        is_running=True,
        last_status="running",
        last_message="Идёт обновление курсов…",
        last_started_at=started_at,
    )
    logger.info("Запущено обновление (%s)", trigger)

    try:
        ok, message = run_update_process()
        finished_at = now_vladivostok()
        _set_update_state(
            is_running=False,
            last_status="success" if ok else "error",
            last_message=message,
            last_finished_at=finished_at,
        )
        if ok:
            logger.info("Обновление завершено успешно (%s)", trigger)
        else:
            logger.error("Обновление завершено с ошибкой (%s): %s", trigger, message)
    finally:
        update_lock.release()


def start_background_update(trigger: str = "manual") -> bool:
    if not update_lock.acquire(blocking=False):
        return False

    worker = threading.Thread(target=_run_update_with_reserved_lock, args=(trigger,), daemon=True)
    worker.start()
    return True


def run_scheduled_update() -> None:
    started = start_background_update(trigger="scheduled")
    if not started:
        logger.info("Плановое обновление пропущено: уже идёт другой запуск")



def start_scheduler_once() -> None:
    global scheduler, scheduler_started

    if scheduler_started or os.environ.get("DISABLE_AUTO_SCHEDULER") == "1":
        return

    scheduler = BackgroundScheduler(timezone=VLADIVOSTOK_TZ)
    scheduler.add_job(
        run_scheduled_update,
        trigger=CronTrigger(hour=10, minute=0, timezone=VLADIVOSTOK_TZ),
        id="daily-rates-update",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    scheduler_started = True
    logger.info("Планировщик запущен: ежедневное обновление в 10:00 Asia/Vladivostok")
    atexit.register(lambda: scheduler.shutdown(wait=False) if scheduler else None)


start_scheduler_once()


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
    payload = load_rates()
    previous_payload = load_previous_history_for_deltas(payload.get("date"))
    show_changes = previous_payload is not None

    data = dict(payload)
    data["rows"] = enrich_rows_with_deltas(
        payload.get("rows", []),
        previous_payload.get("rows", []) if previous_payload else [],
        show_changes,
    )
    for row in data["rows"]:
        row["symbol"] = CURRENCY_SYMBOLS.get(row.get("code"), row.get("code") or "—")

    update_status = get_update_status_payload()

    return render_template(
        "index.html",
        data=data,
        csrf_token=get_csrf_token(),
        show_changes=show_changes,
        update_status=update_status,
    )


@app.route("/refresh", methods=["POST"])
def refresh():
    form_token = request.form.get("csrf_token", "") or request.headers.get("X-CSRF-Token", "")
    if not secrets.compare_digest(form_token, session.get("csrf_token", "")):
        abort(400, description="Неверный токен формы")

    started = start_background_update(trigger="manual")
    if request.accept_mimetypes.best == "application/json" or request.headers.get("X-Requested-With") == "fetch":
        if started:
            return jsonify({"ok": True, "message": "Обновление запущено."})
        return jsonify({"ok": False, "message": "Обновление уже выполняется."}), 409

    if started:
        flash("Обновление запущено.", "success")
    else:
        flash("Обновление уже выполняется.", "error")
    return redirect(url_for("index"))


@app.route("/api/update-status", methods=["GET"])
def api_update_status():
    return jsonify(get_update_status_payload())


@app.route("/health", methods=["GET"])
def health():
    payload = load_rates()
    return jsonify(
        {
            "ok": True,
            "latest_date": payload.get("date"),
            "updated_at_vladivostok": payload.get("updated_at_vladivostok"),
            "scheduler_enabled": scheduler_started,
            "update_status": get_update_status_payload(),
        }
    )


@app.route("/api/rates", methods=["GET"])
def api_rates():
    return jsonify(load_rates())


@app.route("/api/latest.json", methods=["GET"])
def api_latest():
    return jsonify(load_rates())


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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
