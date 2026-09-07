import json
import time
from urllib import request

from .application import HEARTBEAT_FILE
from .config import ConfigurationError, load_settings

MAX_HEARTBEAT_AGE_SECONDS = 90


def main():
    heartbeat_healthy = (
        HEARTBEAT_FILE.is_file()
        and time.time() - HEARTBEAT_FILE.stat().st_mtime < MAX_HEARTBEAT_AGE_SECONDS
    )
    try:
        settings = load_settings()
        with request.urlopen(
            f'http://127.0.0.1:{settings.delivery_api_port}/healthz',
            timeout=2,
        ) as response:
            payload = json.loads(response.read(1024).decode('utf-8'))
            api_healthy = response.getcode() == 200 and payload == {'ok': True}
    except (ConfigurationError, OSError, ValueError, json.JSONDecodeError):
        api_healthy = False
    return 0 if heartbeat_healthy and api_healthy else 1


if __name__ == '__main__':
    raise SystemExit(main())
