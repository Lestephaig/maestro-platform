import logging
import signal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from telegram_bot.application import HEARTBEAT_FILE, build_application

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Запускает Telegram-бота Maestro в режиме long polling.'

    def handle(self, *args, **options):
        del args, options
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError('TELEGRAM_BOT_TOKEN is required')

        HEARTBEAT_FILE.unlink(missing_ok=True)
        application = build_application()
        logger.info('telegram_polling_starting', extra={'event': 'telegram_polling_starting'})
        application.run_polling(
            poll_interval=0.5,
            timeout=settings.TELEGRAM_POLL_TIMEOUT,
            bootstrap_retries=-1,
            close_loop=True,
            stop_signals=(signal.SIGINT, signal.SIGTERM),
        )
