# ✅ Чеклист для деплоя Maestro Platform

## 📋 Подготовка к деплою

### 1. Переменные окружения

Убедитесь, что все необходимые переменные окружения установлены на вашей платформе деплоя:

#### Обязательные:
- `SECRET_KEY` - секретный ключ Django (сгенерируйте новый для production!)
- `DEBUG=False` - обязательно для production
- `ALLOWED_HOSTS` - ваш домен, например: `yourdomain.com,www.yourdomain.com`
- `SITE_URL` - полный URL вашего сайта, например: `https://yourdomain.com`
- `TELEGRAM_BOT_NAME` и `TELEGRAM_LINK_API_TOKEN` — имя бота и отдельный секрет
  привязки аккаунтов
- `TELEGRAM_DELIVERY_API_URL` — HTTPS endpoint либо явно разрешённый HTTP endpoint
  на белом IP зарубежного Telegram gateway
- `TELEGRAM_DELIVERY_API_TOKEN` — отдельный секрет доставки, не совпадающий с
  `TELEGRAM_LINK_API_TOKEN`
- `TELEGRAM_DELIVERY_ALLOW_INSECURE_HTTP=True` — только для HTTP по белому IP;
  при HTTPS оставить `False`

`TELEGRAM_BOT_TOKEN` должен отсутствовать на сервере платформы и храниться только
на зарубежном сервере бота. До перезапуска worker проверьте `GET /healthz` и
авторизованный тестовый POST gateway; недоступность gateway не должна мешать
сохранению сообщений и приводит к повтору записи `NotificationDelivery`.
При прямом HTTP порт gateway должен принимать подключения только с публичного IP
платформы. IP-фильтрация не шифрует Bearer-токен, поэтому HTTPS остаётся более
безопасным вариантом.

#### База данных:
- `DATABASE_URL` - автоматически устанавливается на Heroku/Render, или вручную:
  ```
  postgresql://user:password@host:port/dbname
  ```

#### Redis:
- `REDIS_URL` - для WebSocket чатов, например: `redis://:password@host:port/0`

#### Email:
- `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
- `EMAIL_HOST` - SMTP сервер
- `EMAIL_PORT` - обычно 587
- `EMAIL_USE_TLS=True`
- `EMAIL_HOST_USER` - ваш email
- `EMAIL_HOST_PASSWORD` - пароль приложения
- `DEFAULT_FROM_EMAIL` - email отправителя

#### Безопасность (опционально, но рекомендуется):
- `CSRF_TRUSTED_ORIGINS` - ваш домен с HTTPS, например: `https://yourdomain.com`
- `SECURE_SSL_REDIRECT=True` - для принудительного HTTPS

---

## 🚀 Деплой на Heroku

### Шаги:

1. **Установите Heroku CLI** и войдите:
   ```bash
   heroku login
   ```

2. **Создайте приложение**:
   ```bash
   heroku create your-app-name
   ```

3. **Добавьте PostgreSQL**:
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

4. **Добавьте Redis**:
   ```bash
   heroku addons:create heroku-redis:mini
   ```

5. **Установите переменные окружения**:
   ```bash
   heroku config:set SECRET_KEY=your-secret-key
   heroku config:set DEBUG=False
   heroku config:set ALLOWED_HOSTS=your-app-name.herokuapp.com
   heroku config:set SITE_URL=https://your-app-name.herokuapp.com
   heroku config:set EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
   # ... и другие переменные
   ```

6. **Деплой**:
   ```bash
   git push heroku main
   ```

7. **Примените миграции** (автоматически через release команду в Procfile):
   ```bash
   heroku run python manage.py migrate
   ```

8. **Создайте суперпользователя**:
   ```bash
   heroku run python manage.py createsuperuser
   ```

9. **Соберите статические файлы**:
   ```bash
   heroku run python manage.py collectstatic --noinput
   ```

### Настройка периодических задач (для уведомлений):

Для проверки непрочитанных сообщений каждые 5 минут используйте Heroku Scheduler:

1. Установите аддон:
   ```bash
   heroku addons:create scheduler:standard
   ```

2. Настройте задачу в панели Heroku:
   - Команда: `python manage.py check_unread_messages`
   - Частота: каждые 10 минут

---

## 🌐 Деплой на Render

### Шаги:

1. **Подключите репозиторий** на Render.com

2. **Создайте Web Service**:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `daphne -b 0.0.0.0:$PORT core.asgi:application`

3. **Создайте PostgreSQL Database** и подключите к сервису

4. **Создайте Redis Instance** и подключите к сервису

5. **Установите переменные окружения** в настройках сервиса

6. **Создайте Background Worker** (опционально, для периодических задач):
   - Start Command: `python manage.py check_unread_messages`
   - Или используйте cron job на сервере

---

## 🔧 Деплой на VPS (Ubuntu/Debian)

### Шаги:

1. **Установите зависимости**:
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv postgresql redis-server nginx
   ```

2. **Клонируйте репозиторий**:
   ```bash
   git clone https://github.com/yourusername/maestro-platform.git
   cd maestro-platform
   ```

3. **Создайте виртуальное окружение**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Настройте PostgreSQL**:
   ```bash
   sudo -u postgres psql
   CREATE DATABASE maestro_db;
   CREATE USER maestro_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE maestro_db TO maestro_user;
   \q
   ```

5. **Создайте .env файл**:
   ```bash
   cp .env.example .env
   nano .env
   # Заполните все необходимые переменные
   ```

6. **Примените миграции**:
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py createsuperuser
   ```

7. **Настройте systemd service** для Django:
   Создайте `/etc/systemd/system/maestro.service`:
   ```ini
   [Unit]
   Description=Maestro Platform Django App
   After=network.target

   [Service]
   User=www-data
   Group=www-data
   WorkingDirectory=/path/to/maestro-platform
   Environment="PATH=/path/to/maestro-platform/venv/bin"
   ExecStart=/path/to/maestro-platform/venv/bin/daphne -b 127.0.0.1 -p 8000 core.asgi:application

   [Install]
   WantedBy=multi-user.target
   ```

8. **Настройте Nginx**:
   Создайте `/etc/nginx/sites-available/maestro`:
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;

       location /static/ {
           alias /path/to/maestro-platform/staticfiles/;
       }

       location /media/ {
           alias /path/to/maestro-platform/media/;
       }

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

9. **Настройте SSL** (Let's Encrypt):
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d yourdomain.com
   ```

10. **Настройте cron для периодических задач**:
    ```bash
    crontab -e
    # Добавьте:
    */5 * * * * cd /path/to/maestro-platform && /path/to/venv/bin/python manage.py check_unread_messages
    ```

---

## ✅ Проверка после деплоя

- [ ] Сайт открывается по домену
- [ ] Статические файлы загружаются (CSS, JS)
- [ ] Медиа файлы доступны
- [ ] Регистрация работает
- [ ] Email отправляется (проверьте настройки)
- [ ] WebSocket чаты работают (проверьте Redis)
- [ ] Админка доступна
- [ ] Миграции применены
- [ ] Логи не показывают критических ошибок

---

## 🔍 Отладка

### Просмотр логов:

**Heroku:**
```bash
heroku logs --tail
```

**Render:**
Логи доступны в панели управления

**VPS:**
```bash
sudo journalctl -u maestro -f
tail -f /path/to/maestro-platform/logs/django.log
```

### Частые проблемы:

1. **Статические файлы не загружаются**:
   - Убедитесь, что выполнили `collectstatic`
   - Проверьте настройки `STATIC_ROOT` и `STATIC_URL`

2. **WebSocket не работает**:
   - Проверьте, что Redis запущен и доступен
   - Проверьте `REDIS_URL` в переменных окружения

3. **Email не отправляется**:
   - Проверьте настройки SMTP
   - Убедитесь, что используете пароль приложения (не обычный пароль)

4. **Ошибки базы данных**:
   - Проверьте `DATABASE_URL`
   - Убедитесь, что миграции применены

---

## 📝 Дополнительные рекомендации

1. **Резервное копирование**: Настройте автоматическое резервное копирование базы данных
2. **Мониторинг**: Используйте Sentry или аналогичный сервис для отслеживания ошибок
3. **CDN**: Рассмотрите использование CDN для статических файлов
4. **Кэширование**: Настройте Redis для кэширования (опционально)

---

**Готово к деплою!** 🎉

