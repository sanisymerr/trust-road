# Опубликованный дашборд на Render

Сайт: [trust-road.onrender.com](https://trust-road.onrender.com/). 7 октября 2026 года подтверждены успешный деплой Render, открытие без авторизации, фильтры, мобильное отображение и CSV. Онлайн-версия использует то же оформление, что и автономный HTML.

Репозиторий: [sanisymerr/trust-road](https://github.com/sanisymerr/trust-road). Сервис: [Trust Road в Render](https://dashboard.render.com/web/srv-d6k24l3h46gs73e6ue2g). Ветка публикации — `main`.

| Настройка действующего сервиса | Значение |
|---|---|
| Runtime | Python 3 |
| Build Command | `python -m compileall -q serve.py` |
| Start Command | `bash run.sh` |
| Health Check Path | `/health` |
| Root Directory | Корень репозитория |
| Порт | Переменная Render `PORT`, обычно 10000 |

`run.sh` запускает `serve.py`. Сервер отдаёт готовую страницу и статические материалы из `dashboard`, сжимает HTML через gzip и поддерживает кэширование. Для публикации дополнительные пакеты не нужны; `requirements.txt` предназначен для notebook, подготовки данных и альтернативного Streamlit-приложения. Проверка состояния также доступна по `/_stcore/health`.

## Как обновить сайт

1. При изменении данных пересоберите таблицы и HTML: `python prepare_data.py`, затем `python export_dashboard.py` в окружении с зависимостями из `requirements.txt`.
2. Проверьте изменения локально через `python serve.py`.
3. Загрузите изменения в ветку `main`. Для ручного запуска выберите **Manual Deploy → Deploy latest commit** в Render.
4. Проверьте статус Live, открытие сайта и значения новых данных; согласуйте с ними текст и иллюстрации отчёта.

`render.yaml` — альтернативная конфигурация нового сервиса через Blueprint. Он не является способом автоматического обновления Settings действующего сервиса. Для Blueprint указан Python 3.12.14; файл `.python-version` задаёт серию 3.12.

## Сохранённая прежняя версия

До замены создана ветка [archive/trust-road-before-sdg3-20261007](https://github.com/sanisymerr/trust-road/tree/archive/trust-road-before-sdg3-20261007), содержащая прежний проект. История Git сохранена. Восстановление прежнего приложения потребует вернуть его код и команды сборки и запуска.

Официальные инструкции: [деплои Render](https://render.com/docs/deploys), [версии Python](https://render.com/docs/python-version), [бесплатный тариф](https://render.com/docs/free).
