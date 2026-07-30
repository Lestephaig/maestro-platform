# Repository guide for coding agents

## Project overview

Maestro Platform is a Django 5.2 application for classical-music performers,
agents, clients, announcements, projects, chat, and notifications. The project
uses Django templates (no separate frontend build), Channels for WebSockets,
Redis as the channel layer, and PostgreSQL in deployed environments. SQLite is
the development fallback.

## Repository map

- `core/` — project settings, root URLs, middleware, shared views, and legal
  document loading.
- `accounts/` — custom user model, authentication, profiles, and legal
  acceptance records.
- `performers/`, `agents/`, `clients/` — role-specific profiles and views.
- `announcements/` — listings and matching tags.
- `interactions/` — projects and participant workflow.
- `chat/` — chat rooms and Channels consumers.
- `notifications/` — in-app/email notifications and signal handlers.
- `templates/`, `static/` — shared server-rendered UI and assets.
- `docs/maestro/` — legal DOCX sources used at runtime by `core/legal.py`.

## Local setup

Use the repository virtual environment when it exists:

```powershell
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

On Unix-like systems, use `python` and `cp` instead. SQLite works without
Docker. Redis is required for real WebSocket traffic; start the services with
`docker compose up -d db redis` when needed.

## Required verification

Run the narrowest relevant tests while developing. Before handing off a
substantial change, run:

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

If the virtual environment is absent, use the available Python interpreter.
For deployment changes, also run `docker compose config`.

## Change conventions

- Keep business logic in the owning Django app; avoid adding unrelated logic to
  `core`.
- Preserve server-rendered templates and progressive enhancement. Put shared
  UI in root `templates/`/`static/` and app-specific UI inside the app.
- Add tests to the affected app. Cover permissions, role boundaries, and
  notification side effects when relevant.
- Create migrations for model changes; never edit an applied migration merely
  to make migration history look cleaner.
- Use named URLs and keep the existing `interactions` and `notifications`
  namespaces intact.
- Read configuration through `python-decouple`; document new variables in
  `.env.example` without real credentials.
- Do not rename or remove files in `docs/maestro/` without updating
  `core/legal.py`. These documents are application data, not archival docs.
- Treat `.env`, databases, media, logs, IDE state, and virtual environments as
  local-only files.

## Safety notes

- The custom user model is `accounts.User`; do not replace it with Django's
  default user model.
- Changes to legal acceptance, authentication, permissions, email, deployment,
  or production security settings need explicit regression coverage or a
  documented manual check.
- Do not weaken production security settings to simplify local development.
- Preserve unrelated working-tree changes and never commit secrets or generated
  files.
