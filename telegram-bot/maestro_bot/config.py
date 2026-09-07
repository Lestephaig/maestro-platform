from dataclasses import dataclass
from pathlib import Path

from decouple import AutoConfig

SERVICE_ROOT = Path(__file__).resolve().parent.parent


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class BotSettings:
    token: str
    name: str
    maestro_base_url: str
    maestro_api_token: str
    delivery_api_token: str = ''
    delivery_api_host: str = '0.0.0.0'
    delivery_api_port: int = 8080
    delivery_db_path: str = '/app/data/delivery.sqlite3'
    connect_timeout: float = 5
    read_timeout: float = 20
    write_timeout: float = 20
    pool_timeout: float = 5
    poll_timeout: int = 30


def load_settings() -> BotSettings:
    config = AutoConfig(search_path=SERVICE_ROOT)
    token = config('TELEGRAM_BOT_TOKEN', default='').strip()
    name = config('TELEGRAM_BOT_NAME', default='').strip().lstrip('@')
    maestro_base_url = config('MAESTRO_BASE_URL', default='').strip().rstrip('/')
    maestro_api_token = config('MAESTRO_API_TOKEN', default='').strip()
    delivery_api_token = config('TELEGRAM_DELIVERY_API_TOKEN', default='').strip()
    delivery_api_host = config(
        'TELEGRAM_DELIVERY_API_HOST', default='0.0.0.0'
    ).strip()
    delivery_api_port = config('TELEGRAM_DELIVERY_API_PORT', default=8080, cast=int)
    delivery_db_path = config(
        'TELEGRAM_DELIVERY_DB_PATH', default='/app/data/delivery.sqlite3'
    ).strip()

    missing = [
        variable
        for variable, value in (
            ('TELEGRAM_BOT_TOKEN', token),
            ('TELEGRAM_BOT_NAME', name),
            ('MAESTRO_BASE_URL', maestro_base_url),
            ('MAESTRO_API_TOKEN', maestro_api_token),
            ('TELEGRAM_DELIVERY_API_TOKEN', delivery_api_token),
            ('TELEGRAM_DELIVERY_API_HOST', delivery_api_host),
            ('TELEGRAM_DELIVERY_DB_PATH', delivery_db_path),
        )
        if not value
    ]
    if missing:
        raise ConfigurationError(f'Missing required variables: {", ".join(missing)}')
    if not maestro_base_url.startswith(('http://', 'https://')):
        raise ConfigurationError('MAESTRO_BASE_URL must start with http:// or https://')
    if maestro_api_token == delivery_api_token:
        raise ConfigurationError(
            'MAESTRO_API_TOKEN and TELEGRAM_DELIVERY_API_TOKEN must be different'
        )
    if not 1 <= delivery_api_port <= 65535:
        raise ConfigurationError('TELEGRAM_DELIVERY_API_PORT must be between 1 and 65535')

    settings = BotSettings(
        token=token,
        name=name,
        maestro_base_url=maestro_base_url,
        maestro_api_token=maestro_api_token,
        delivery_api_token=delivery_api_token,
        delivery_api_host=delivery_api_host,
        delivery_api_port=delivery_api_port,
        delivery_db_path=delivery_db_path,
        connect_timeout=config('TELEGRAM_CONNECT_TIMEOUT', default=5, cast=float),
        read_timeout=config('TELEGRAM_READ_TIMEOUT', default=20, cast=float),
        write_timeout=config('TELEGRAM_WRITE_TIMEOUT', default=20, cast=float),
        pool_timeout=config('TELEGRAM_POOL_TIMEOUT', default=5, cast=float),
        poll_timeout=config('TELEGRAM_POLL_TIMEOUT', default=30, cast=int),
    )
    timeout_values = (
        settings.connect_timeout,
        settings.read_timeout,
        settings.write_timeout,
        settings.pool_timeout,
        settings.poll_timeout,
    )
    if any(value <= 0 for value in timeout_values):
        raise ConfigurationError('Telegram timeouts must be positive')
    return settings
