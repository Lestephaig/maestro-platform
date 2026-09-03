# Отдельный Telegram-бот Maestro

Этот каталог является самостоятельным Python-сервисом. Он не использует Django,
базу данных, Redis, `.env`, Dockerfile или Compose-файл основной платформы. Каталог
можно отдельно скопировать на выделенный Linux-сервер.

Бот получает обновления через **long polling**: входящий порт, публичный webhook и
общая Docker-сеть с платформой не нужны. Для одного токена запускайте только один
экземпляр polling-процесса.

## Конфигурация

```shell
cd telegram-bot
cp .env.example .env
nano .env
sudo chown "$(id -u):10001" .env
chmod 640 .env
```

Обязательные переменные в локальном `telegram-bot/.env`:

- `TELEGRAM_BOT_TOKEN` — токен от BotFather;
- `TELEGRAM_BOT_NAME` — username бота без `@`;
- `MAESTRO_BASE_URL` — публичный URL основной платформы.
- `MAESTRO_API_TOKEN` — отдельный случайный секрет для запросов привязки к
  платформе; значение должно совпадать с `TELEGRAM_LINK_API_TOKEN` в `.env`
  Django-приложения.

Для production `MAESTRO_BASE_URL` должен использовать HTTPS: бот отправляет на
платформу одноразовый токен привязки и числовой Telegram `chat_id`. Telegram bot
token в Django-приложение не передаётся.

Этот файл не используется платформой и исключён из Git и Docker build context.
Compose монтирует его в контейнер как `/app/.env` в режиме read-only, поэтому секрет
не попадает в образ. GID `10001` — группа непривилегированного пользователя
внутри образа; права `640` оставляют файл доступным боту, но не остальным пользователям.

## Запуск в Docker

Из каталога `telegram-bot`:

```shell
docker compose build
docker compose up -d
docker compose ps
docker compose logs -f telegram-bot
```

Контейнер запускается от непривилегированного пользователя, имеет политику
`restart: unless-stopped` и healthcheck по heartbeat-файлу.

После изменения `.env` пересобирать образ не нужно. Перезапустите процесс, чтобы он
заново прочитал настройки из смонтированного файла:

```shell
nano .env
docker compose restart telegram-bot
```

## Локальный запуск и тесты

```shell
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m maestro_bot
.venv/bin/python -m unittest discover -s tests -v
```

В Windows используйте `.venv\\Scripts\\python.exe`.

## Внутренний сервис отправки

Модуль `maestro_bot.service` формирует inline-клавиатуру, применяет таймауты и
возвращает `False` вместо распространения ошибки Telegram API. Токен, `chat_id` и
текст сообщения не записываются в логи.

Сейчас это локальный Python API внутри сервиса. Поскольку платформа и бот находятся
на разных серверах, будущую отправку уведомлений из платформы нужно подключать через
отдельный аутентифицированный сетевой контракт или очередь. Публиковать токен бота в
`.env` платформы для этого не следует.

## Привязка аккаунта

В профиле Maestro пользователь запрашивает ссылку вида
`https://t.me/<bot>?start=<одноразовый токен>`. Платформа хранит только SHA-256-хеш
токена; ссылка действует 15 минут, а новая ссылка аннулирует предыдущую. Допускается
не более пяти запросов ссылок за 15 минут на пользователя.

Команда `/start <token>` работает только в личном чате. Бот передаёт токен и
числовой `chat_id` в
`/accounts/api/telegram/link/complete/` с заголовком `Authorization: Bearer ...`.
Username Telegram не используется и не сохраняется. Endpoint’ы статуса, создания
ссылки и отвязки используют обычную Django-сессию и CSRF-защиту.
