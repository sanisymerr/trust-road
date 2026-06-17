# Trust Road — QR Payment Portal

Рабочее Flask-приложение для создания QR-кодов с двуязычными банковскими реквизитами.

## Администратор

- Логин: `trust`
- Пароль: `binance`
- Локальный адрес: `http://127.0.0.1:5001/admin`
- Рабочий адрес: `https://trust-road.onrender.com/admin`

## Стандартные поля

При создании карточки форма уже содержит названия полей, но значения остаются пустыми:

- Получатель / Beneficiary
- Юридический или фактический адрес / Legal or actual address
- Телефон / Telephone
- E-mail
- Банк / Bank
- Адрес банка / Bank address
- Номер счёта или IBAN / Account number or IBAN
- SWIFT или BIC
- Директор или контактное лицо / Director or contact person

Пустые поля не отображаются клиенту.

## Возможности

- создание, редактирование, отключение и удаление карточек;
- русский и английский язык;
- копирование отдельных реквизитов и всей карточки;
- QR в PNG, SVG и PDF;
- адаптация под iPhone, Android, iPad, macOS и Windows;
- SQLite локально и PostgreSQL на Render.

## Локальный запуск на Mac

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
PORT=5001 python3 app.py
```

Открыть: `http://127.0.0.1:5001/admin`

## Настройки существующего сервиса Render

- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn --bind 0.0.0.0:$PORT app:app`
- Health Check Path: `/health`

Переменные окружения:

```text
ADMIN_USERNAME=trust
ADMIN_PASSWORD=binance
PUBLIC_BASE_URL=https://trust-road.onrender.com
FLASK_DEBUG=0
SESSION_COOKIE_SECURE=1
SECRET_KEY=<длинная случайная строка>
DATABASE_URL=<Internal Database URL из Render Postgres>
```

Без `DATABASE_URL` приложение запустится на SQLite, но на Render данные могут исчезнуть после пересборки или перезапуска сервиса.
