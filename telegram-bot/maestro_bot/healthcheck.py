import time

from .application import HEARTBEAT_FILE

MAX_HEARTBEAT_AGE_SECONDS = 90


def main():
    healthy = (
        HEARTBEAT_FILE.is_file()
        and time.time() - HEARTBEAT_FILE.stat().st_mtime < MAX_HEARTBEAT_AGE_SECONDS
    )
    return 0 if healthy else 1


if __name__ == '__main__':
    raise SystemExit(main())
