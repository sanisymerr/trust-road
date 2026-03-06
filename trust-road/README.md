# Trust Road

Минималистичный белый сайт, который:
- берет свежие курсы с страницы Capitron Bank,
- использует последний столбец `Бэлэн бус → Зарах`,
- считает итог в MNT,
- считает итог в RUB через курс RUB из той же таблицы.

## Запуск локально

```bash
cd trust-road
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Render

### Build Command
```bash
pip install -r requirements.txt
```

### Start Command
```bash
python app.py
```

Если на хостинге снова будет ошибка SSL, в коде уже есть fallback: сначала идет нормальная проверка сертификата через `certifi`, затем запасной запрос.
