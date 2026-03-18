from flask import Flask, render_template, jsonify, abort

app = Flask(__name__)

STORE = {
    "name": "NEONOVA",
    "tagline": "Маркетплейс электроники и техники",
    "description": "Смартфоны, ноутбуки, аудио, устройства для умного дома и gaming-товары — в одном каталоге с удобной фильтрацией, сортировкой и корзиной.",
    "creators": ["Александр Зейда", "Игорь Бочаров", "София Чукина"],
}

POPULAR_BRANDS = [
    "Apple", "Samsung", "Xiaomi", "HUAWEI", "Sony", "JBL", "Яндекс", "Aqara", "ASUS", "HyperX", "Logitech"
]

CATEGORIES = [
    {"slug": "smartphones", "name": "Смартфоны", "icon": "smartphone"},
    {"slug": "laptops", "name": "Ноутбуки", "icon": "laptop"},
    {"slug": "audio", "name": "Аудио", "icon": "headphones"},
    {"slug": "smart-home", "name": "Умный дом", "icon": "home"},
    {"slug": "gaming", "name": "Гейминг", "icon": "gamepad-2"},
]

PRODUCTS = [
    {
        "id": 1,
        "slug": "apple-iphone-15",
        "name": "Apple iPhone 15",
        "category": "smartphones",
        "price": 89990,
        "rating": 4.9,
        "badge": "Хит",
        "short_description": "Смартфон Apple с OLED-дисплеем, Dynamic Island и двойной камерой.",
        "description": "Apple iPhone 15 — популярная модель для повседневного использования, фото, видео и экосистемы Apple.",
        "image": "products/apple-iphone-15.jpg",
        "specs": ["6.1″ OLED", "128 ГБ", "Dynamic Island", "USB-C"],
    },
    {
        "id": 2,
        "slug": "samsung-galaxy-s24",
        "name": "Samsung Galaxy S24",
        "category": "smartphones",
        "price": 74990,
        "rating": 4.8,
        "badge": "Новинка",
        "short_description": "Компактный флагман Samsung с AMOLED-экраном и мощной камерой.",
        "description": "Samsung Galaxy S24 подойдёт тем, кто ищет производительный Android-смартфон для фото, работы и повседневных задач.",
        "image": "products/samsung-galaxy-s24.jpg",
        "specs": ["6.2″ AMOLED", "128 ГБ", "50 МП", "5G"],
    },
    {
        "id": 3,
        "slug": "xiaomi-redmi-note-13-pro",
        "name": "Xiaomi Redmi Note 13 Pro",
        "category": "smartphones",
        "price": 37990,
        "rating": 4.7,
        "badge": "Выгодно",
        "short_description": "Смартфон Xiaomi с большим экраном, высокой автономностью и камерой 200 МП.",
        "description": "Xiaomi Redmi Note 13 Pro — удобный вариант для тех, кому нужен современный смартфон с хорошим экраном и запасом памяти.",
        "image": "products/xiaomi-redmi-note-13-pro.jpg",
        "specs": ["6.67″ AMOLED", "8 ГБ RAM / 256 ГБ", "200 МП", "Turbo Charge"],
    },
    {
        "id": 4,
        "slug": "apple-macbook-air-13-m2",
        "name": "Apple MacBook Air 13 M2",
        "category": "laptops",
        "price": 124990,
        "rating": 4.9,
        "badge": "Премиум",
        "short_description": "Лёгкий ноутбук Apple для учёбы, работы и повседневных задач.",
        "description": "Apple MacBook Air 13 M2 — один из самых узнаваемых ноутбуков в категории ультрабуков с долгой автономностью и тонким корпусом.",
        "image": "products/apple-macbook-air-13-m2.jpg",
        "specs": ["13.6″", "Apple M2", "16 ГБ RAM", "SSD 256 ГБ"],
    },
    {
        "id": 5,
        "slug": "huawei-matebook-d-16",
        "name": "HUAWEI MateBook D 16",
        "category": "laptops",
        "price": 99990,
        "rating": 4.8,
        "badge": "Популярно",
        "short_description": "Ноутбук с большим экраном и удобной клавиатурой для работы и учёбы.",
        "description": "HUAWEI MateBook D 16 подойдёт для офисных задач, работы с документами, браузером и повседневной многозадачности.",
        "image": "products/huawei-matebook-d-16.jpg",
        "specs": ["16″ IPS", "Intel Core i5", "16 ГБ RAM", "SSD 512 ГБ"],
    },
    {
        "id": 6,
        "slug": "asus-vivobook-15",
        "name": "ASUS VivoBook 15",
        "category": "laptops",
        "price": 87990,
        "rating": 4.7,
        "badge": "Для учёбы",
        "short_description": "Универсальный ноутбук ASUS для дома, офиса и учебных задач.",
        "description": "ASUS VivoBook 15 — распространённая модель в среднем сегменте с привычным форм-фактором и удобным экраном 15.6 дюйма.",
        "image": "products/asus-vivobook-15.jpg",
        "specs": ["15.6″ FHD", "Intel Core i5", "16 ГБ RAM", "SSD 512 ГБ"],
    },
    {
        "id": 7,
        "slug": "apple-airpods-pro-2",
        "name": "Apple AirPods Pro 2",
        "category": "audio",
        "price": 21990,
        "rating": 4.9,
        "badge": "Топ",
        "short_description": "Беспроводные наушники Apple с активным шумоподавлением и кейсом MagSafe.",
        "description": "Apple AirPods Pro 2 — популярная TWS-модель для звонков, музыки и использования с устройствами Apple.",
        "image": "products/apple-airpods-pro-2.png",
        "specs": ["ANC", "USB-C", "Bluetooth 5.3", "MagSafe Case"],
    },
    {
        "id": 8,
        "slug": "sony-wh-1000xm5",
        "name": "Sony WH-1000XM5",
        "category": "audio",
        "price": 34990,
        "rating": 4.9,
        "badge": "Шумоподавление",
        "short_description": "Полноразмерные наушники Sony для музыки, поездок и работы.",
        "description": "Sony WH-1000XM5 — одна из самых узнаваемых моделей в сегменте полноразмерных Bluetooth-наушников с ANC.",
        "image": "products/sony-wh-1000xm5.jpg",
        "specs": ["Bluetooth 5.2", "ANC", "Микрофоны для звонков", "До 30 часов"],
    },
    {
        "id": 9,
        "slug": "jbl-charge-5",
        "name": "JBL Charge 5",
        "category": "audio",
        "price": 14990,
        "rating": 4.8,
        "badge": "Портативно",
        "short_description": "Портативная колонка JBL с влагозащитой и мощным звуком.",
        "description": "JBL Charge 5 подходит для дома, поездок и отдыха на улице: узнаваемый корпус, автономность и насыщенный звук.",
        "image": "products/jbl-charge-5.jpg",
        "specs": ["Bluetooth", "IP67", "До 20 часов", "Функция Powerbank"],
    },
    {
        "id": 10,
        "slug": "aqara-hub-m2",
        "name": "Aqara Hub M2",
        "category": "smart-home",
        "price": 8990,
        "rating": 4.7,
        "badge": "Хаб",
        "short_description": "Центр управления устройствами умного дома Aqara.",
        "description": "Aqara Hub M2 объединяет совместимые устройства в единую систему управления и подходит как база для сценариев умного дома.",
        "image": "products/aqara-hub-m2.png",
        "specs": ["Zigbee 3.0", "IR-управление", "Поддержка сценариев", "Компактный корпус"],
    },
    {
        "id": 11,
        "slug": "yandex-station-midi",
        "name": "Яндекс Станция Миди",
        "category": "smart-home",
        "price": 14990,
        "rating": 4.8,
        "badge": "Алиса",
        "short_description": "Умная колонка с Алисой и встроенным Zigbee-хабом.",
        "description": "Яндекс Станция Миди подойдёт для музыки, голосового управления и базовых сценариев умного дома.",
        "image": "products/yandex-station-midi.jpg",
        "specs": ["Алиса", "Zigbee", "Bluetooth 5.0", "24 Вт"],
    },
    {
        "id": 12,
        "slug": "xiaomi-smart-camera-c300",
        "name": "Xiaomi Smart Camera C300",
        "category": "smart-home",
        "price": 5990,
        "rating": 4.8,
        "badge": "Безопасность",
        "short_description": "Домашняя IP-камера Xiaomi с ночной съёмкой и поворотным механизмом.",
        "description": "Xiaomi Smart Camera C300 подходит для наблюдения за домом, комнатой или рабочим пространством через приложение.",
        "image": "products/xiaomi-smart-camera-c300.png",
        "specs": ["2304x1296", "Ночной режим", "Поворотный механизм", "Wi‑Fi"],
    },
    {
        "id": 13,
        "slug": "hyperx-alloy-origins",
        "name": "HyperX Alloy Origins",
        "category": "gaming",
        "price": 8990,
        "rating": 4.8,
        "badge": "Игровой",
        "short_description": "Механическая клавиатура HyperX с RGB-подсветкой.",
        "description": "HyperX Alloy Origins — популярная игровая клавиатура с металлической рамой и яркой подсветкой.",
        "image": "products/hyperx-alloy-origins.jpg",
        "specs": ["Механические переключатели", "RGB", "USB", "Русская раскладка"],
    },
    {
        "id": 14,
        "slug": "logitech-g102-lightsync",
        "name": "Logitech G102 Lightsync",
        "category": "gaming",
        "price": 2490,
        "rating": 4.8,
        "badge": "Точность",
        "short_description": "Игровая мышь Logitech с RGB-подсветкой и 6 кнопками.",
        "description": "Logitech G102 Lightsync — одна из самых узнаваемых игровых мышей начального сегмента.",
        "image": "products/logitech-g102-lightsync.jpg",
        "specs": ["8000 DPI", "6 кнопок", "RGB", "Проводное подключение"],
    },
    {
        "id": 15,
        "slug": "samsung-odyssey-g5-27",
        "name": "Samsung Odyssey G5 27″",
        "category": "gaming",
        "price": 32990,
        "rating": 4.8,
        "badge": "144 Гц",
        "short_description": "Игровой монитор Samsung с изогнутым экраном и высокой частотой обновления.",
        "description": "Samsung Odyssey G5 27″ — заметная модель среди игровых мониторов с QHD-разрешением и плавной картинкой.",
        "image": "products/samsung-odyssey-g5-27.jpg",
        "specs": ["27″ QHD", "144 Гц", "1 мс", "Изогнутый экран"],
    },
]

CATEGORY_MAP = {item["slug"]: item for item in CATEGORIES}
PRODUCT_MAP = {item["slug"]: item for item in PRODUCTS}


def enrich_product(product):
    category = CATEGORY_MAP.get(product["category"], {})
    enriched = dict(product)
    enriched["category_name"] = category.get("name", "Без категории")
    return enriched


@app.context_processor
def inject_globals():
    return {
        "store": STORE,
        "categories": CATEGORIES,
        "cart_enabled": True,
    }


@app.route("/")
def index():
    featured_slugs = [
        "apple-iphone-15",
        "apple-macbook-air-13-m2",
        "apple-airpods-pro-2",
        "yandex-station-midi",
        "hyperx-alloy-origins",
        "samsung-odyssey-g5-27",
    ]
    featured = [enrich_product(PRODUCT_MAP[slug]) for slug in featured_slugs]
    top_categories = []
    for category in CATEGORIES:
        count = len([product for product in PRODUCTS if product["category"] == category["slug"]])
        top_categories.append({**category, "count": count})
    return render_template(
        "index.html",
        featured=featured,
        top_categories=top_categories,
        products_count=len(PRODUCTS),
        creators=STORE["creators"],
        popular_brands=POPULAR_BRANDS,
    )


@app.route("/catalog")
def catalog():
    enriched_products = [enrich_product(item) for item in PRODUCTS]
    return render_template(
        "catalog.html",
        products=enriched_products,
        categories=CATEGORIES,
    )


@app.route("/product/<slug>")
def product_detail(slug):
    product = PRODUCT_MAP.get(slug)
    if not product:
        abort(404)
    related = [
        enrich_product(item)
        for item in PRODUCTS
        if item["category"] == product["category"] and item["slug"] != slug
    ][:3]
    return render_template(
        "product.html",
        product=enrich_product(product),
        related=related,
    )


@app.route("/cart")
def cart():
    return render_template("cart.html")



@app.route("/about")
def about():
    return render_template("about.html", creators=STORE["creators"])


@app.route("/api/products")
def api_products():
    return jsonify([enrich_product(item) for item in PRODUCTS])


if __name__ == "__main__":
    app.run(debug=True)
