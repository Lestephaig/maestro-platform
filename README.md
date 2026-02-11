# Maestro Platform

MVP платформы для классических музыкантов и заказчиков.

## Local development

1. Создайте и активируйте виртуальное окружение.
2. Установите зависимости:
   - `pip install -r requirements.txt`
3. Скопируйте `.env.example` в `.env` и заполните значения.
4. Примените миграции:
   - `python manage.py migrate`
5. Запустите сервер:
   - `python manage.py runserver`

## Production checklist

- `DEBUG=False`
- корректный `SECRET_KEY` (длинный случайный ключ)
- заполнены `ALLOWED_HOSTS` и `CSRF_TRUSTED_ORIGINS`
- настроен `DATABASE_URL` (PostgreSQL)
- настроен `REDIS_URL` для Channels
- настроен SMTP (`EMAIL_*`)
- задан `SITE_URL` (https URL вашего домена)

## Deployment notes

- Приложение запускается как ASGI через Daphne (см. `Procfile`).
- В `release` команде выполняются:
  - миграции
  - `collectstatic`
- Для раздачи статики включен WhiteNoise (`USE_WHITENOISE=True` по умолчанию).

## Security

При `DEBUG=False` автоматически включаются:

- secure cookies (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`)
- HSTS
- защита от sniffing (`SECURE_CONTENT_TYPE_NOSNIFF`)
- `X_FRAME_OPTIONS=DENY`

Дополнительно управляется через `.env`:

- `SECURE_SSL_REDIRECT`
- `SECURE_HSTS_SECONDS`
- `SECURE_HSTS_INCLUDE_SUBDOMAINS`
- `SECURE_HSTS_PRELOAD`
- `USE_X_FORWARDED_HOST`
