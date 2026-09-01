# Telegram-бот Maestro

Бот работает как отдельный процесс того же Django-проекта. Для получения
обновлений выбран **long polling**. Он не требует публичного webhook-маршрута,
сертифика и изменений Nginx, поэтому хорошо соответствует текущей инфраструктуре.
В Compose у сервиса нет зависимостей от web, PostgreSQL и Redis, поэтому его можно запустить
отдельно на выделенном Linux-сервере.
Запускать можно только один polling-процесс для одного токена.

## Конфигурация

Обязательны для запуска:

- `TELEGRAM_BOT_TOKEN` — токен от BotFather;
- `TELEGRAM_BOT_NAME` — username бота без `@`;
- `MAESTRO_BASE_URL` — публичный URL Maestro.

Таймауты можно изменить через `TELEGRAM_CONNECT_TIMEOUT`, `TELEGRAM_READ_TIMEOUT`,
`TELEGRAM_WRITE_TIMEOUT`, `TELEGRAM_POOL_TIMEOUT` и `TELEGRAM_POLL_TIMEOUT`.

## Запуск

```shell
python manage.py run_telegram_bot
```

В Docker Compose:

```shell
docker compose up -d telegram-bot
docker compose ps telegram-bot
docker compose logs -f telegram-bot
```

Сервис имеет `restart: unless-stopped` и healthcheck по обновляемому heartbeat-файлу.
Завершение `SIGINT`/`SIGTERM` корректно останавливает polling и HTTP-клиент.

## Отправка из backend

```python
from telegram_bot.service import TelegramButton, send_telegram_message_sync

sent = send_telegram_message_sync(
    chat_id=123456789,
    text='Тестовое сообщение',
    buttons=[[TelegramButton('Открыть Maestro', 'https://www.maestrocast.ru/')]],
)
```

Для async-кода используйте `await send_telegram_message(...)`. Метод возвращает `False`
при ошибке Telegram API и не передаёт её в бизнес-сценарий. В логи не попадают токен,
`chat_id` или текст сообщения.
