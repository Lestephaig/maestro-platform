FROM python:3.11-slim

WORKDIR /app

# Установим зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Создаем папки
RUN mkdir -p /app/staticfiles /app/media /app/private_media /app/logs

# Собираем статику
RUN python manage.py collectstatic --noinput

ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=core.settings

EXPOSE 8000

# Запускаем через daphne
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "core.asgi:application"]
