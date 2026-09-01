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
```

Обязательные переменные в локальном `telegram-bot/.env`:

- `TELEGRAM_BOT_TOKEN` — токен от BotFather;
- `TELEGRAM_BOT_NAME` — username бота без `@`;
- `MAESTRO_BASE_URL` — публичный URL основной платформы.

Этот файл не используется платформой и исключён из Git и Docker build context.

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
