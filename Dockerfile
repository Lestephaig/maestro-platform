FROM python:3.11-slim

WORKDIR /app

# Системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# Создаем папки
RUN mkdir -p /app/staticfiles /app/media /app/logs

# Собираем статику
RUN python manage.py collectstatic --noinput

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=core.settings

EXPOSE 8000

# Запуск через daphne (Channels)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "core.asgi:application"]