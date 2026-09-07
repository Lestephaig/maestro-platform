import logging
import signal

from .application import HEARTBEAT_FILE, build_application
from .config import ConfigurationError, load_settings
from .logging_config import configure_logging


def main():
    configure_logging()
    logger = logging.getLogger(__name__)
    try:
        settings = load_settings()
    except (ConfigurationError, ValueError) as error:
        logger.critical(
            'telegram_configuration_invalid',
            extra={
                'event': 'telegram_configuration_invalid',
                'error_type': type(error).__name__,
            },
        )
        return 2

    HEARTBEAT_FILE.unlink(missing_ok=True)
    application = build_application(settings)
    logger.info('telegram_polling_starting', extra={'event': 'telegram_polling_starting'})
    application.run_polling(
        poll_interval=0.5,
        timeout=settings.poll_timeout,
        bootstrap_retries=-1,
        close_loop=True,
        stop_signals=(signal.SIGINT, signal.SIGTERM),
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
