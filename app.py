import io
import json
import os
import re
import secrets
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path

import qrcode
import qrcode.image.svg
from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.middleware.proxy_fix import ProxyFix


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def normalize_database_url(value: str) -> str:
    """Convert legacy postgres:// URLs and provide a local SQLite fallback."""
    if not value:
        return f"sqlite:///{DATA_DIR / 'app.db'}"
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://"):]
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://"):]
    return value


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "local-development-secret-change-on-render")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
app.config.update(
    SQLALCHEMY_DATABASE_URI=normalize_database_url(os.getenv("DATABASE_URL", "")),
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

if os.getenv("SESSION_COOKIE_SECURE", "0") == "1":
    app.config["SESSION_COOKIE_SECURE"] = True

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "trust")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "binance")


STANDARD_FIELDS = [
    {"label_ru": "Получатель", "label_en": "Beneficiary", "value_ru": "", "value_en": ""},
    {"label_ru": "Юридический / фактический адрес", "label_en": "Legal / actual address", "value_ru": "", "value_en": ""},
    {"label_ru": "Телефон", "label_en": "Telephone", "value_ru": "", "value_en": ""},
    {"label_ru": "E-mail", "label_en": "E-mail", "value_ru": "", "value_en": ""},
    {"label_ru": "Банк", "label_en": "Bank", "value_ru": "", "value_en": ""},
    {"label_ru": "Адрес банка", "label_en": "Bank address", "value_ru": "", "value_en": ""},
    {"label_ru": "Номер счёта / IBAN", "label_en": "Account number / IBAN", "value_ru": "", "value_en": ""},
    {"label_ru": "SWIFT / BIC", "label_en": "SWIFT / BIC", "value_ru": "", "value_en": ""},
    {"label_ru": "Директор / контактное лицо", "label_en": "Director / contact person", "value_ru": "", "value_en": ""},
]


def standard_fields():
    return [dict(field) for field in STANDARD_FIELDS]

db = SQLAlchemy(app)


class PaymentPage(db.Model):
    __tablename__ = "payment_pages"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(60), unique=True, nullable=False, index=True)
    company = db.Column(db.String(300), nullable=False)
    title_ru = db.Column(db.String(300), nullable=False)
    title_en = db.Column(db.String(300), nullable=False)
    subtitle_ru = db.Column(db.Text, nullable=False, default="")
    subtitle_en = db.Column(db.Text, nullable=False, default="")
    fields_json = db.Column(db.Text, nullable=False)
    note_ru = db.Column(db.Text, nullable=False, default="")
    note_en = db.Column(db.Text, nullable=False, default="")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False)

    @property
    def fields(self):
        try:
            value = json.loads(self.fields_json)
            return value if isinstance(value, list) else []
        except (TypeError, json.JSONDecodeError):
            return []

    def to_dict(self):
        return {
            "id": self.id,
            "slug": self.slug,
            "company": self.company,
            "title_ru": self.title_ru,
            "title_en": self.title_en,
            "subtitle_ru": self.subtitle_ru or "",
            "subtitle_en": self.subtitle_en or "",
            "fields": self.fields,
            "note_ru": self.note_ru or "",
            "note_en": self.note_en or "",
            "is_active": bool(self.is_active),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


with app.app_context():
    db.create_all()


def utc_now():
    return datetime.now(timezone.utc)


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def make_slug():
    return secrets.token_urlsafe(9).replace("-", "").replace("_", "")[:12].lower()


def clean_slug(value):
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-").lower()
    return cleaned[:60]


def get_page_or_404(slug):
    page = db.session.execute(
        db.select(PaymentPage).where(PaymentPage.slug == slug)
    ).scalar_one_or_none()
    if page is None:
        abort(404)
    return page


def parse_fields_from_form():
    labels_ru = request.form.getlist("label_ru[]")
    labels_en = request.form.getlist("label_en[]")
    values_ru = request.form.getlist("value_ru[]")
    values_en = request.form.getlist("value_en[]")

    count = max(len(labels_ru), len(labels_en), len(values_ru), len(values_en), 0)
    fields = []

    for index in range(count):
        label_ru = labels_ru[index].strip() if index < len(labels_ru) else ""
        label_en = labels_en[index].strip() if index < len(labels_en) else ""
        value_ru = values_ru[index].strip() if index < len(values_ru) else ""
        value_en = values_en[index].strip() if index < len(values_en) else ""

        # Предустановленные строки с пустыми значениями не попадают на публичную страницу.
        if not (value_ru or value_en):
            continue

        if not (label_ru or label_en):
            raise ValueError("У заполненного поля должно быть название хотя бы на одном языке.")

        fields.append(
            {
                "label_ru": label_ru or label_en,
                "label_en": label_en or label_ru,
                "value_ru": value_ru or value_en,
                "value_en": value_en or value_ru,
            }
        )

    return fields


def absolute_public_url(slug):
    configured = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if configured:
        return f"{configured}{url_for('public_page', slug=slug)}"
    return url_for("public_page", slug=slug, _external=True)


def create_qr(slug, *, box_size=14):
    target_url = absolute_public_url(slug)
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=4,
    )
    qr.add_data(target_url)
    qr.make(fit=True)
    return qr


@app.before_request
def csrf_protection():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)

    if request.method == "POST":
        submitted = request.form.get("csrf_token", "")
        expected = session.get("csrf_token", "")
        if not submitted or not secrets.compare_digest(submitted, expected):
            abort(400, description="Сессия формы устарела. Обновите страницу и повторите действие.")


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": session.get("csrf_token", "")}


@app.route("/")
def home():
    return redirect(url_for("admin_dashboard"))


@app.route("/health")
def health():
    return {"status": "ok"}, 200


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logged_in"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        valid_username = secrets.compare_digest(username, ADMIN_USERNAME)
        valid_password = secrets.compare_digest(password, ADMIN_PASSWORD)

        if valid_username and valid_password:
            csrf_token = session.get("csrf_token")
            session.clear()
            session["csrf_token"] = csrf_token or secrets.token_urlsafe(32)
            session["admin_logged_in"] = True
            flash("Вход выполнен.", "success")

            next_url = request.args.get("next", "")
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("admin_dashboard"))

        flash("Неверный логин или пароль.", "error")

    return render_template("login.html")


@app.post("/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    pages = db.session.execute(
        db.select(PaymentPage).order_by(PaymentPage.id.desc())
    ).scalars().all()
    return render_template(
        "admin_dashboard.html",
        pages=[page.to_dict() for page in pages],
    )


def form_values(page=None):
    if request.method == "POST":
        return {
            "company": request.form.get("company", ""),
            "title_ru": request.form.get("title_ru", ""),
            "title_en": request.form.get("title_en", ""),
            "subtitle_ru": request.form.get("subtitle_ru", ""),
            "subtitle_en": request.form.get("subtitle_en", ""),
            "note_ru": request.form.get("note_ru", ""),
            "note_en": request.form.get("note_en", ""),
            "slug": request.form.get("slug", ""),
        }
    if page:
        return page.to_dict()
    return {
        "company": "",
        "title_ru": "Реквизиты для перевода",
        "title_en": "Payment details",
        "subtitle_ru": "Данные для банковского перевода",
        "subtitle_en": "Bank transfer details",
        "note_ru": "Перед отправкой перевода проверьте получателя, номер счёта и SWIFT / BIC.",
        "note_en": "Before sending the transfer, verify the beneficiary, account number and SWIFT / BIC.",
        "slug": "",
    }


@app.route("/admin/new", methods=["GET", "POST"])
@admin_required
def admin_create():
    fields = standard_fields()

    if request.method == "POST":
        try:
            fields = parse_fields_from_form()
        except ValueError as error:
            flash(str(error), "error")
            return render_template(
                "admin_form.html",
                mode="create",
                page=None,
                values=form_values(),
                fields=fields,
            )

        values = form_values()
        company = values["company"].strip()
        title_ru = values["title_ru"].strip()
        title_en = values["title_en"].strip()
        custom_slug = clean_slug(values["slug"])
        slug = custom_slug or make_slug()

        if not company or not title_ru or not title_en:
            flash("Заполните компанию и заголовки на русском и английском.", "error")
            return render_template(
                "admin_form.html",
                mode="create",
                page=None,
                values=values,
                fields=fields or standard_fields(),
            )

        if not fields:
            flash("Добавьте хотя бы одно поле с реквизитами.", "error")
            return render_template(
                "admin_form.html",
                mode="create",
                page=None,
                values=values,
                fields=standard_fields(),
            )

        now = utc_now()
        page = PaymentPage(
            slug=slug,
            company=company,
            title_ru=title_ru,
            title_en=title_en,
            subtitle_ru=values["subtitle_ru"].strip(),
            subtitle_en=values["subtitle_en"].strip(),
            fields_json=json.dumps(fields, ensure_ascii=False),
            note_ru=values["note_ru"].strip(),
            note_en=values["note_en"].strip(),
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.session.add(page)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Такой короткий адрес уже используется. Укажите другой.", "error")
            return render_template(
                "admin_form.html",
                mode="create",
                page=None,
                values=values,
                fields=fields,
            )

        flash("QR-страница создана.", "success")
        return redirect(url_for("admin_result", slug=page.slug))

    return render_template(
        "admin_form.html",
        mode="create",
        page=None,
        values=form_values(),
        fields=fields,
    )


@app.route("/admin/<slug>/edit", methods=["GET", "POST"])
@admin_required
def admin_edit(slug):
    page = get_page_or_404(slug)
    fields = page.fields

    if request.method == "POST":
        try:
            fields = parse_fields_from_form()
        except ValueError as error:
            flash(str(error), "error")
            return render_template(
                "admin_form.html",
                mode="edit",
                page=page.to_dict(),
                values=form_values(page),
                fields=fields,
            )

        values = form_values(page)
        company = values["company"].strip()
        title_ru = values["title_ru"].strip()
        title_en = values["title_en"].strip()

        if not company or not title_ru or not title_en or not fields:
            flash("Заполните обязательные поля и добавьте реквизиты.", "error")
            return render_template(
                "admin_form.html",
                mode="edit",
                page=page.to_dict(),
                values=values,
                fields=fields or standard_fields(),
            )

        page.company = company
        page.title_ru = title_ru
        page.title_en = title_en
        page.subtitle_ru = values["subtitle_ru"].strip()
        page.subtitle_en = values["subtitle_en"].strip()
        page.fields_json = json.dumps(fields, ensure_ascii=False)
        page.note_ru = values["note_ru"].strip()
        page.note_en = values["note_en"].strip()
        page.is_active = request.form.get("is_active") == "on"
        page.updated_at = utc_now()
        db.session.commit()

        flash("Изменения сохранены.", "success")
        return redirect(url_for("admin_result", slug=slug))

    return render_template(
        "admin_form.html",
        mode="edit",
        page=page.to_dict(),
        values=form_values(page),
        fields=fields,
    )


@app.route("/admin/<slug>/result")
@admin_required
def admin_result(slug):
    page = get_page_or_404(slug).to_dict()
    return render_template(
        "admin_result.html",
        page=page,
        public_url=absolute_public_url(slug),
    )


@app.post("/admin/<slug>/toggle")
@admin_required
def admin_toggle(slug):
    page = get_page_or_404(slug)
    page.is_active = not page.is_active
    page.updated_at = utc_now()
    db.session.commit()
    flash("Статус страницы изменён.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/admin/<slug>/delete")
@admin_required
def admin_delete(slug):
    page = get_page_or_404(slug)
    db.session.delete(page)
    db.session.commit()
    flash("Страница удалена.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/p/<slug>")
def public_page(slug):
    page = get_page_or_404(slug)
    if not page.is_active:
        abort(404)
    return render_template("public_page.html", page=page.to_dict())


def qr_access_allowed(page):
    return page.is_active or session.get("admin_logged_in")


@app.route("/qr/<slug>.png")
def qr_png(slug):
    page = get_page_or_404(slug)
    if not qr_access_allowed(page):
        abort(404)

    image = create_qr(slug, box_size=16).make_image(
        fill_color="#0f172a", back_color="white"
    ).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, "PNG", optimize=True)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="image/png",
        as_attachment=request.args.get("download") == "1",
        download_name=f"{slug}-qr.png",
        max_age=0,
    )


@app.route("/qr/<slug>.svg")
def qr_svg(slug):
    page = get_page_or_404(slug)
    if not qr_access_allowed(page):
        abort(404)

    target_url = absolute_public_url(slug)
    image = qrcode.make(
        target_url,
        image_factory=qrcode.image.svg.SvgPathImage,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        border=4,
    )
    buffer = io.BytesIO()
    image.save(buffer)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="image/svg+xml",
        as_attachment=request.args.get("download") == "1",
        download_name=f"{slug}-qr.svg",
        max_age=0,
    )


@app.route("/qr/<slug>.pdf")
def qr_pdf(slug):
    page = get_page_or_404(slug)
    if not qr_access_allowed(page):
        abort(404)

    image = create_qr(slug, box_size=24).make_image(
        fill_color="black", back_color="white"
    ).convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, "PDF", resolution=300.0)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{slug}-qr.pdf",
        max_age=0,
    )


@app.errorhandler(400)
def bad_request(error):
    return render_template(
        "error.html",
        code=400,
        title="Не удалось выполнить действие",
        message=getattr(error, "description", "Обновите страницу и повторите попытку."),
    ), 400


@app.errorhandler(404)
def not_found(_error):
    return render_template(
        "error.html",
        code=404,
        title="Страница недоступна",
        message="QR-ссылка не найдена или была отключена администратором.",
    ), 404


@app.errorhandler(500)
def server_error(_error):
    db.session.rollback()
    return render_template(
        "error.html",
        code=500,
        title="Внутренняя ошибка",
        message="Попробуйте обновить страницу. Если ошибка повторяется, проверьте журнал сервера.",
    ), 500


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5001"))
    debug = os.getenv("FLASK_DEBUG", "1") == "1"
    app.run(host=host, port=port, debug=debug)
