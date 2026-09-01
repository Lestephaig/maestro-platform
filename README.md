# Maestro Platform

MVP платформы для классических музыкантов и заказчиков.

## Возможности

- профили исполнителей, агентов и заказчиков;
- объявления и отклики;
- проекты и взаимодействие участников;
- чат через Django Channels;
- уведомления в интерфейсе и по email;
- публикация и фиксация принятия юридических документов.

## Локальная разработка

Требуется Python 3.10+.

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

В Linux/macOS активируйте окружение обычным способом и используйте `python`
вместо пути к `python.exe`. Без `DATABASE_URL` приложение использует SQLite.
Redis нужен для WebSocket-чата; PostgreSQL и Redis можно запустить командой:

```shell
docker compose up -d db redis
```

## Проверки

```shell
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

## Структура

- `core/` — настройки проекта, общие URL, middleware и юридические документы;
- `accounts/`, `performers/`, `agents/`, `clients/` — пользователи и профили;
- `announcements/`, `interactions/`, `chat/`, `notifications/` — предметные
  приложения;
- `templates/`, `static/` — общий серверный интерфейс;
- `docs/maestro/` — DOCX-файлы, которые приложение отображает как юридические
  документы.

Подробные правила для Codex и других coding agents находятся в
[`AGENTS.md`](AGENTS.md).

## Развёртывание

Приложение запускается как ASGI через Daphne. Инструкции и production checklist:

- [`DEPLOYMENT.md`](DEPLOYMENT.md);
- [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md).
- [`telegram-bot/README.md`](telegram-bot/README.md) — отдельный сервис Telegram-бота.
