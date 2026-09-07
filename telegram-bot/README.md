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
- `TELEGRAM_DELIVERY_API_TOKEN` — отдельный Bearer-секрет входящего API доставки;
  значение должно совпадать с одноимённой переменной платформы и не должно
  совпадать с `MAESTRO_API_TOKEN`.
- `TELEGRAM_DELIVERY_API_HOST` и `TELEGRAM_DELIVERY_API_PORT` — адрес внутреннего
  HTTP-сервера (по умолчанию `0.0.0.0:8080`).
- `TELEGRAM_DELIVERY_DB_PATH` — SQLite-файл реестра идемпотентности на Docker
  volume (по умолчанию `/app/data/delivery.sqlite3`).
- `TELEGRAM_DELIVERY_PUBLISH_HOST` — интерфейс публикации Docker-порта. По
  умолчанию `127.0.0.1`; для прямого доступа по белому IP установите `0.0.0.0` и
  ограничьте TCP/8080 firewall-правилом до IP платформы.

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
`restart: unless-stopped`; healthcheck одновременно проверяет heartbeat polling
и `GET /healthz`. По умолчанию порт API публикуется только как
`127.0.0.1:8080`.

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

## Delivery API

Платформа вызывает:

```http
POST /internal/v1/telegram/messages
Authorization: Bearer <TELEGRAM_DELIVERY_API_TOKEN>
Idempotency-Key: notification-delivery-<delivery_id>
Content-Type: application/json
```

Тело содержит положительный `chat_id`, непустой `text` до 4096 символов,
`parse_mode: "HTML"` и массив строк HTTPS inline-кнопок `buttons`. Успех и
повтор уже завершённого ключа возвращают `200` с `telegram_message_id`; для
повтора устанавливается `duplicate: true`. Некорректный ввод возвращает `400`
или `413`, неверная авторизация — `401`, окончательный отказ Telegram — `422`,
rate limit — `429`, временные сбои — `502/503`.

Сервис хранит в SQLite только SHA-256-хеш idempotency key, статус, Telegram
message ID и время. Успешные записи старше семи дней очищаются; параллельный
запрос с уже обрабатываемым ключом не отправляется второй раз. Строгое
`exactly once` невозможно гарантировать, если процесс завершится после принятия
сообщения Telegram, но до фиксации результата в SQLite.

Внутренний порт следует публиковать через HTTPS reverse proxy. Минимальный
фрагмент Nginx:

```nginx
location = /internal/v1/telegram/messages {
    client_max_body_size 16k;
    proxy_connect_timeout 5s;
    proxy_read_timeout 30s;
    proxy_pass http://127.0.0.1:8080;
}

location = /healthz {
    proxy_pass http://127.0.0.1:8080;
}
```

На публичном endpoint нужен действительный TLS-сертификат. При постоянном IP
платформы дополнительно ограничьте доступ к маршруту по IP, не убирая Bearer-
аутентификацию.

### Прямой HTTP по белому IP

Если DNS и TLS отсутствуют, в `telegram-bot/.env` задайте:

```env
TELEGRAM_DELIVERY_PUBLISH_HOST=0.0.0.0
```

После перезапуска API будет опубликован как `http://<PUBLIC_IP>:8080`. На
firewall зарубежного сервера разрешите TCP/8080 только с публичного IP платформы;
для остальных источников порт должен быть закрыт. На платформе задайте:

```env
TELEGRAM_DELIVERY_API_URL=http://<PUBLIC_IP>:8080/internal/v1/telegram/messages
TELEGRAM_DELIVERY_ALLOW_INSECURE_HTTP=True
```

Production-проверка принимает такой opt-in только для глобального IP-адреса и
отклоняет hostname, loopback и приватные адреса. Bearer-аутентификация остаётся
обязательной. При этом HTTP не шифрует token, `chat_id` и текст на сетевом пути;
IP allowlist уменьшает доступность endpoint, но не заменяет TLS.

## Внутренний сервис отправки

Модуль `maestro_bot.service` формирует inline-клавиатуру, применяет таймауты и
возвращает безопасную категорию ошибки Telegram API. Объект Bot и его пул
соединений совместно используются polling и delivery API. BotFather-токен
хранится только на зарубежном сервере; токен, `chat_id` и текст сообщения не
записываются в логи.

## Порядок развёртывания и ручная проверка

1. Создайте новый секрет (`openssl rand -hex 32`) и задайте его как
   `TELEGRAM_DELIVERY_API_TOKEN` на обоих серверах.
2. Сначала разверните бот и volume. Настройте либо HTTPS reverse proxy, либо
   прямую публикацию по белому IP с firewall allowlist. Проверьте `/healthz` с
   сервера платформы.
3. Выполните авторизованный тестовый POST с новым уникальным
   `Idempotency-Key`; повтор того же POST должен вернуть `duplicate: true`.
4. Только затем задайте `TELEGRAM_DELIVERY_API_URL`, token и timeout на
   платформе и разверните web/worker.
5. Отправьте реальное сообщение и убедитесь, что `NotificationDelivery`
   перешёл в `sent`; после этого удалите старый `TELEGRAM_BOT_TOKEN` из `.env`
   платформы.

Для проверки восстановления перезапустите оба сервиса и повторите запрос с уже
успешным ключом: Telegram не должен получить второе сообщение.

Пример POST (подставьте тестовый chat ID и секрет из окружения, не сохраняйте
команду с секретом в shell history):

```shell
curl --fail-with-body https://bot.example.com/internal/v1/telegram/messages \
  -H "Authorization: Bearer $TELEGRAM_DELIVERY_API_TOKEN" \
  -H "Idempotency-Key: manual-check-$(date +%s)" \
  -H "Content-Type: application/json" \
  --data '{"chat_id":123456789,"text":"Gateway check","parse_mode":"HTML","buttons":[]}'
```

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
