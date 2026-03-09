TrustRoad — локальный сайт с таблицей курсов валют

Что делает сайт:
- показывает таблицу курсов валют;
- Монголбанк и Capitron отображаются в MNT;
- ЦБ РФ отображается в RUB;
- есть кнопка ручного обновления;
- есть автообновление каждый день в 12:00 по Владивостоку.

Команды для Mac после распаковки в Downloads:

cd ~/Downloads/trustroad_table_site
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python update_data.py
python app.py

Открыть в браузере:
http://127.0.0.1:5000

Быстрый запуск:

bash run.sh

Важно:
- если обновление не проходит, сначала проверь интернет;
- браузер Chromium для Playwright надо установить один раз командой:
  python -m playwright install chromium
