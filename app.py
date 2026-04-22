import json
import os
import sqlite3
from contextlib import closing
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "medved.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "medved-soft-gifts-secret-key")
app.config["DATABASE"] = str(DB_PATH)

PRODUCTS = [
    {
        "name": "Мишка Classic",
        "category": "Товар",
        "price": 2500,
        "short_description": "Мягкий подарок с именной биркой и деликатной упаковкой.",
        "description": "Нежный базовый медведь ручной работы для первого заказа, дня рождения или тёплого знака внимания. Хорошо подходит для персональной бирки, выбора оттенка и лаконичного оформления.",
        "image_emoji": "🧸",
        "features": ["ручная работа", "именная бирка", "мягкая палитра", "подарочная упаковка"],
        "accent": "blush",
    },
    {
        "name": "Мишка Premium",
        "category": "Товар",
        "price": 3900,
        "short_description": "Подарок с аксессуарами, открыткой и расширенной кастомизацией.",
        "description": "Премиальная версия для важной даты: можно выбрать цвет, аксессуар, открытку с посланием и более выразительную упаковку. Идеально для вау-эффекта при вручении.",
        "image_emoji": "🎁",
        "features": ["выбор цвета", "аксессуары", "открытка", "премиум упаковка"],
        "accent": "rose",
    },
    {
        "name": "Мишка Love Story",
        "category": "Товар",
        "price": 4700,
        "short_description": "Романтичный подарок для пары, годовщины или памятной даты.",
        "description": "Модель с романтичной эстетикой: персональная надпись, декоративная лента, тематическое оформление и возможность добавить послание с историей вашего события.",
        "image_emoji": "💗",
        "features": ["романтичный стиль", "индивидуальная надпись", "лента", "история подарка"],
        "accent": "pearl",
    },
    {
        "name": "Подарочный сет для малыша",
        "category": "Товар",
        "price": 5200,
        "short_description": "Нежный набор для ребёнка: игрушка, карточка и мягкая подарочная подача.",
        "description": "Комплект с безопасной эстетикой и спокойной палитрой. Подходит для рождения малыша, крестин, первого дня рождения и памятных семейных моментов.",
        "image_emoji": "🍼",
        "features": ["семейный подарок", "спокойные оттенки", "карточка", "упаковка"],
        "accent": "sand",
    },
    {
        "name": "Срочный заказ 48 часов",
        "category": "Услуга",
        "price": 1200,
        "short_description": "Приоритет в производстве и согласовании заказа.",
        "description": "Ускорим подготовку подарка, если он нужен к конкретной дате. Подходит, когда важен дедлайн и нужен приоритет в очереди производства.",
        "image_emoji": "⚡",
        "features": ["приоритетный пошив", "быстрое согласование", "ускоренная упаковка"],
        "accent": "blush",
    },
    {
        "name": "Подарочная упаковка Deluxe",
        "category": "Услуга",
        "price": 700,
        "short_description": "Коробка, лента, карточка и аккуратная подарочная подача.",
        "description": "Дополнительная упаковка для тех, кто хочет готовый к вручению подарок с мягким вау-эффектом и эстетичной презентацией.",
        "image_emoji": "🎀",
        "features": ["коробка", "карточка", "лента", "эффект"],
        "accent": "rose",
    },
    {
        "name": "Корпоративный заказ",
        "category": "Услуга",
        "price": 5500,
        "short_description": "Индивидуальный расчёт для брендов, мероприятий и команд.",
        "description": "Подберём тираж в фирменной эстетике: оттенки, карточки, брендированные элементы, единый стиль упаковки и аккуратную подачу для партнёров или команды.",
        "image_emoji": "🏷️",
        "features": ["брендирование", "партия изделий", "единый стиль", "индивидуальный расчёт"],
        "accent": "pearl",
    },
    {
        "name": "Персональная открытка",
        "category": "Услуга",
        "price": 450,
        "short_description": "Короткое послание, которое делает подарок по-настоящему личным.",
        "description": "Поможем оформить мини-послание в красивой карточке: от нежной подписи до истории памятной даты. Отлично дополняет основной подарок.",
        "image_emoji": "💌",
        "features": ["тёплый текст", "аккуратный дизайн", "готово к вручению"],
        "accent": "sand",
    },
]

COLOR_OPTIONS = ["Кремовый", "Пудрово-розовый", "Молочный", "Карамельный", "Светло-бежевый", "Нежно-серый"]
ACCESSORY_OPTIONS = [
    "Без аксессуара",
    "Атласный бант",
    "Шёлковая лента",
    "Мини-букет",
    "Сердечко из фетра",
    "Именная подвеска",
    "Колпачок ко дню рождения",
]
PACKAGING_OPTIONS = [
    "Стандартная",
    "Подарочная коробка",
    "Deluxe с лентой",
    "Праздничный пакет",
    "Романтичная подача",
]
OCCASION_OPTIONS = [
    "Без повода",
    "День рождения",
    "Годовщина",
    "Свидание",
    "Для ребёнка",
    "Благодарность",
    "Корпоративный подарок",
]
CARD_OPTIONS = [
    "Без открытки",
    "Короткое послание",
    "Именная карточка",
    "Открытка с историей",
]
PAYMENT_OPTIONS = ["Баланс", "Оплата при получении"]


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if session.get("user_id") is None:
            flash("Сначала войдите в профиль, чтобы продолжить.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(**kwargs)

    return wrapped_view


def init_db():
    db = sqlite3.connect(app.config["DATABASE"])
    with closing(db.cursor()) as cur:
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                phone TEXT,
                balance REAL NOT NULL DEFAULT 0,
                role TEXT NOT NULL DEFAULT 'client'
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL,
                short_description TEXT NOT NULL,
                description TEXT NOT NULL,
                image_emoji TEXT NOT NULL,
                features_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                total REAL NOT NULL,
                payment_method TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                options_json TEXT NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            );
            """
        )
        db.commit()

    seed_db(db)
    db.close()


def seed_db(db: sqlite3.Connection):
    cur = db.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        users = [
            (
                "Александр Зейда",
                "alex@medved.app",
                generate_password_hash("123456"),
                "+7 914 680-06-20",
                15000,
                "client",
            ),
            (
                "София Чукина",
                "sofia@medved.app",
                generate_password_hash("123456"),
                "+7 900 000-00-01",
                8000,
                "client",
            ),
            (
                "Менеджер проекта",
                "admin@medved.app",
                generate_password_hash("123456"),
                "+7 900 000-00-99",
                0,
                "admin",
            ),
        ]
        cur.executemany(
            "INSERT INTO users (full_name, email, password_hash, phone, balance, role) VALUES (?, ?, ?, ?, ?, ?)",
            users,
        )

    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO products (name, category, price, short_description, description, image_emoji, features_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    item["name"],
                    item["category"],
                    item["price"],
                    item["short_description"],
                    item["description"],
                    item["image_emoji"],
                    json.dumps(item["features"], ensure_ascii=False),
                )
                for item in PRODUCTS
            ],
        )

    cur.execute("SELECT COUNT(*) FROM orders")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO orders (user_id, total, payment_method, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (1, 4600, "Баланс", "В работе", datetime.now().strftime("%d.%m.%Y %H:%M")),
        )
        order_id = cur.lastrowid
        cur.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price, options_json) VALUES (?, ?, ?, ?, ?)",
            (
                order_id,
                2,
                1,
                3900,
                json.dumps(
                    {
                        "Имя на бирке": "Анна",
                        "Цвет": "Пудрово-розовый",
                        "Аксессуар": "Атласный бант",
                        "Упаковка": "Deluxe с лентой",
                        "Повод": "День рождения",
                        "Открытка": "Короткое послание",
                        "Комментарий": "Нежная подача, мягкая палитра.",
                    },
                    ensure_ascii=False,
                ),
            ),
        )
        cur.execute(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price, options_json) VALUES (?, ?, ?, ?, ?)",
            (
                order_id,
                6,
                1,
                700,
                json.dumps(
                    {"Упаковка": "Deluxe с лентой", "Комментарий": "Добавить открытку с поздравлением."},
                    ensure_ascii=False,
                ),
            ),
        )

    db.commit()


def load_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)


def get_products():
    rows = query_db("SELECT * FROM products ORDER BY id")
    accent_map = {item["name"]: item.get("accent", "blush") for item in PRODUCTS}
    products = []
    for row in rows:
        item = dict(row)
        item["features"] = json.loads(item["features_json"])
        item["accent"] = accent_map.get(item["name"], "blush")
        products.append(item)
    return products


def get_product(product_id: int):
    row = query_db("SELECT * FROM products WHERE id = ?", (product_id,), one=True)
    if not row:
        return None
    item = dict(row)
    item["features"] = json.loads(item["features_json"])
    item["accent"] = next((p.get("accent", "blush") for p in PRODUCTS if p["name"] == item["name"]), "blush")
    return item


def build_product_options(product):
    is_service = product["category"] == "Услуга"
    return {
        "tag_name": {"label": "Имя на бирке или короткая подпись", "placeholder": "Например, Анна", "default": ""},
        "color": {"label": "Цвет", "values": COLOR_OPTIONS if not is_service else ["Не требуется", "Кремовый", "Пудровый", "Бежевый"]},
        "accessory": {"label": "Аксессуар", "values": ACCESSORY_OPTIONS if not is_service else ["Без аксессуара", "Лента", "Карточка", "Наклейка бренда"]},
        "packaging": {"label": "Упаковка", "values": PACKAGING_OPTIONS},
        "occasion": {"label": "Повод", "values": OCCASION_OPTIONS},
        "card": {"label": "Открытка", "values": CARD_OPTIONS},
        "quantity": {"label": "Количество", "default": 1},
        "comment": {"label": "Пожелания к оформлению", "placeholder": "Опишите настроение подарка, повод, цветовую гамму или важные детали"},
    }


def cart_totals(items):
    subtotal = sum(item["price"] * item["quantity"] for item in items)
    service_fee = 0 if subtotal >= 5000 or subtotal == 0 else 290
    grand_total = subtotal + service_fee
    return subtotal, service_fee, grand_total


def merge_cart_item(cart, new_item):
    for item in cart:
        if item["product_id"] == new_item["product_id"] and item["options"] == new_item["options"]:
            item["quantity"] += new_item["quantity"]
            return cart
    cart.append(new_item)
    return cart


@app.context_processor
def inject_globals():
    current_user = load_current_user()
    cart_items = session.get("cart", [])
    return {
        "current_user": current_user,
        "cart_count": sum(item["quantity"] for item in cart_items),
        "brand_tagline": "персональные подарки с историей",
    }


@app.route("/")
def home():
    featured = get_products()[:4]
    benefits = [
        {"icon": "🤍", "title": "Тонкая персонализация", "text": "Имя, оттенок, открытка и аксессуары собираются под конкретного человека и его историю."},
        {"icon": "🪄", "title": "Ручная подача", "text": "Каждый подарок оформляется мягко и аккуратно, чтобы его хотелось сразу вручить."},
        {"icon": "🎀", "title": "Готово к моменту", "text": "Получатель видит не просто игрушку, а цельный подарок с продуманной эстетикой."},
    ]
    moments = ["Для пары", "На день рождения", "Для ребёнка", "На памятную дату"]
    return render_template("home.html", featured=featured, benefits=benefits, moments=moments)


@app.route("/company")
def company():
    stats = [
        {"label": "Средний чек", "value": "2 500–5 000 ₽"},
        {"label": "Темп на старте", "value": "5–10 заказов в месяц"},
        {"label": "Формат", "value": "Студия персональных подарков"},
    ]
    steps = [
        ("Выбираете модель", "Подбираете подарок, который подходит по настроению и поводу."),
        ("Настраиваете детали", "Указываете оттенок, аксессуары, открытку и пожелания."),
        ("Мы собираем подарок", "Аккуратно готовим изделие, проверяем подачу и согласовываем детали."),
        ("Получаете ready-to-gift заказ", "Подарок приезжает уже в красивой и понятной упаковке."),
    ]
    return render_template("company.html", stats=stats, steps=steps)


@app.route("/catalog")
def catalog():
    category = request.args.get("category", "Все")
    products = get_products()
    if category != "Все":
        products = [p for p in products if p["category"] == category]
    return render_template("catalog.html", products=products, category=category)


@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = get_product(product_id)
    if not product:
        flash("Позиция не найдена.", "danger")
        return redirect(url_for("catalog"))
    options = build_product_options(product)
    return render_template("product_detail.html", product=product, options=options)


@app.post("/add-to-cart/<int:product_id>")
def add_to_cart(product_id):
    product = get_product(product_id)
    if not product:
        flash("Позиция не найдена.", "danger")
        return redirect(url_for("catalog"))

    cart = session.get("cart", [])
    quantity = max(1, int(request.form.get("quantity", 1) or 1))
    options = {
        "Имя или подпись": request.form.get("tag_name", "").strip() or "Без подписи",
        "Цвет": request.form.get("color", "Кремовый"),
        "Аксессуар": request.form.get("accessory", "Без аксессуара"),
        "Упаковка": request.form.get("packaging", "Стандартная"),
        "Повод": request.form.get("occasion", "Без повода"),
        "Открытка": request.form.get("card", "Без открытки"),
        "Пожелания": request.form.get("comment", "").strip() or "Без комментария",
    }

    cart_item = {
        "cart_id": f"{product_id}-{datetime.utcnow().timestamp()}",
        "product_id": product_id,
        "name": product["name"],
        "price": product["price"],
        "quantity": quantity,
        "emoji": product["image_emoji"],
        "accent": product.get("accent", "blush"),
        "category": product["category"],
        "options": options,
    }

    session["cart"] = merge_cart_item(cart, cart_item)
    session.modified = True
    flash("Позиция добавлена в корзину.", "success")
    return redirect(url_for("cart"))


@app.route("/cart")
def cart():
    items = session.get("cart", [])
    subtotal, service_fee, grand_total = cart_totals(items)
    return render_template(
        "cart.html",
        items=items,
        subtotal=subtotal,
        service_fee=service_fee,
        grand_total=grand_total,
    )


@app.post("/cart/update/<cart_id>")
def update_cart_item(cart_id):
    quantity = max(1, int(request.form.get("quantity", 1) or 1))
    cart = session.get("cart", [])
    for item in cart:
        if item["cart_id"] == cart_id:
            item["quantity"] = quantity
            break
    session["cart"] = cart
    session.modified = True
    flash("Количество обновлено.", "success")
    return redirect(url_for("cart"))


@app.post("/cart/remove/<cart_id>")
def remove_from_cart(cart_id):
    cart = [item for item in session.get("cart", []) if item["cart_id"] != cart_id]
    session["cart"] = cart
    session.modified = True
    flash("Позиция удалена из корзины.", "info")
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    items = session.get("cart", [])
    if not items:
        flash("Сначала добавьте что-нибудь в корзину.", "warning")
        return redirect(url_for("catalog"))

    current_user = load_current_user()
    subtotal, service_fee, grand_total = cart_totals(items)

    if request.method == "POST":
        payment_method = request.form.get("payment_method", "Баланс")
        db = get_db()
        if payment_method == "Баланс" and current_user["balance"] < grand_total:
            flash("На балансе недостаточно средств. Выберите оплату при получении.", "danger")
            return redirect(url_for("checkout"))

        if payment_method == "Баланс":
            db.execute(
                "UPDATE users SET balance = balance - ? WHERE id = ?",
                (grand_total, current_user["id"]),
            )

        created_at = datetime.now().strftime("%d.%m.%Y %H:%M")
        cur = db.execute(
            "INSERT INTO orders (user_id, total, payment_method, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (current_user["id"], grand_total, payment_method, "Новый", created_at),
        )
        order_id = cur.lastrowid

        for item in items:
            db.execute(
                "INSERT INTO order_items (order_id, product_id, quantity, unit_price, options_json) VALUES (?, ?, ?, ?, ?)",
                (
                    order_id,
                    item["product_id"],
                    item["quantity"],
                    item["price"],
                    json.dumps(item["options"], ensure_ascii=False),
                ),
            )

        db.commit()
        session["cart"] = []
        session.modified = True
        flash("Заказ оформлен. Его можно открыть в профиле.", "success")
        return redirect(url_for("order_success", order_id=order_id))

    return render_template(
        "checkout.html",
        items=items,
        subtotal=subtotal,
        service_fee=service_fee,
        grand_total=grand_total,
        current_user=current_user,
        payment_options=PAYMENT_OPTIONS,
    )


@app.route("/order-success/<int:order_id>")
@login_required
def order_success(order_id):
    order = query_db("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, session["user_id"]), one=True)
    if not order:
        return redirect(url_for("profile"))
    return render_template("order_success.html", order=order)


@app.route("/profile")
def profile_gate():
    current_user = load_current_user()
    if current_user:
        orders = query_db(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC",
            (current_user["id"],),
        )
        return render_template("profile.html", orders=orders, current_user=current_user)

    demo_users = [
        {
            "email": "alex@medved.app",
            "password": "123456",
            "label": "Клиент с историей заказов",
            "description": "Баланс профиля, оформленный заказ и готовая история покупок.",
        },
        {
            "email": "sofia@medved.app",
            "password": "123456",
            "label": "Новый клиентский профиль",
            "description": "Чистый сценарий входа, чтобы показать интерфейс без заказов.",
        },
        {
            "email": "admin@medved.app",
            "password": "123456",
            "label": "Панель менеджера",
            "description": "Список заказов и работа со статусами внутри приложения.",
        },
    ]
    return render_template("login.html", demo_users=demo_users)


@app.route("/order/<int:order_id>")
@login_required
def order_detail(order_id):
    order = query_db("SELECT * FROM orders WHERE id = ? AND user_id = ?", (order_id, session["user_id"]), one=True)
    if not order:
        flash("Заказ не найден.", "danger")
        return redirect(url_for("profile_gate"))
    items = query_db(
        """
        SELECT oi.*, p.name, p.image_emoji
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        WHERE oi.order_id = ?
        """,
        (order_id,),
    )
    parsed_items = []
    for item in items:
        d = dict(item)
        d["options"] = json.loads(d["options_json"])
        parsed_items.append(d)
    return render_template("order_detail.html", order=order, items=parsed_items)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = query_db("SELECT * FROM users WHERE lower(email) = ?", (email,), one=True)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash("Вы вошли в профиль.", "success")
            next_page = request.args.get("next") or url_for("profile_gate")
            return redirect(next_page)
        flash("Проверьте email и пароль.", "danger")
    return redirect(url_for("profile_gate"))


@app.route("/logout")
def logout():
    session.clear()
    flash("Вы вышли из профиля.", "info")
    return redirect(url_for("home"))


@app.route("/admin")
def admin():
    current_user = load_current_user()
    if not current_user or current_user["role"] != "admin":
        flash("Раздел заказов доступен менеджеру проекта.", "warning")
        return redirect(url_for("profile_gate"))
    orders = query_db(
        """
        SELECT o.*, u.full_name
        FROM orders o
        JOIN users u ON u.id = o.user_id
        ORDER BY o.id DESC
        """
    )
    return render_template("admin.html", orders=orders)


@app.post("/admin/order/<int:order_id>/status")
def admin_update_status(order_id):
    current_user = load_current_user()
    if not current_user or current_user["role"] != "admin":
        return redirect(url_for("profile_gate"))
    status = request.form.get("status", "Новый")
    get_db().execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    get_db().commit()
    flash("Статус обновлён.", "success")
    return redirect(url_for("admin"))


@app.route("/manifest.json")
def manifest():
    return jsonify(
        {
            "name": "Медведь и точка",
            "short_name": "Медведь",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#fff8fa",
            "theme_color": "#e4a3b6",
            "icons": [],
        }
    )


@app.route("/service-worker.js")
def service_worker():
    return app.send_static_file("js/service-worker.js")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
