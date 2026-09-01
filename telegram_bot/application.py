import asyncio
import logging
from contextlib import suppress
from pathlib import Path

from django.conf import settings
from telegram.error import TelegramError
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest

from .handlers import BOT_COMMANDS, error_handler, help_command, start_command, unknown_command

logger = logging.getLogger(__name__)
HEARTBEAT_FILE = Path('/tmp/maestro-telegram-bot.heartbeat')


async def _heartbeat():
    while True:
        HEARTBEAT_FILE.touch()
        await asyncio.sleep(30)


async def _post_init(application: Application):
    try:
        await application.bot.set_my_commands(BOT_COMMANDS)
    except TelegramError as error:
        logger.warning(
            'telegram_commands_setup_failed',
            extra={
                'event': 'telegram_commands_setup_failed',
                'error_type': type(error).__name__,
            },
        )
    application.bot_data['heartbeat_task'] = asyncio.create_task(_heartbeat())
    logger.info('telegram_bot_started', extra={'event': 'telegram_bot_started'})


async def _post_shutdown(application: Application):
    task = application.bot_data.pop('heartbeat_task', None)
    if task is not None:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    HEARTBEAT_FILE.unlink(missing_ok=True)
    logger.info('telegram_bot_stopped', extra={'event': 'telegram_bot_stopped'})


def build_application():
    api_request = HTTPXRequest(
        connect_timeout=settings.TELEGRAM_CONNECT_TIMEOUT,
        read_timeout=settings.TELEGRAM_READ_TIMEOUT,
        write_timeout=settings.TELEGRAM_WRITE_TIMEOUT,
        pool_timeout=settings.TELEGRAM_POOL_TIMEOUT,
    )
    updates_request = HTTPXRequest(
        connect_timeout=settings.TELEGRAM_CONNECT_TIMEOUT,
        read_timeout=settings.TELEGRAM_POLL_TIMEOUT + 5,
        write_timeout=settings.TELEGRAM_WRITE_TIMEOUT,
        pool_timeout=settings.TELEGRAM_POOL_TIMEOUT,
    )
    application = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .request(api_request)
        .get_updates_request(updates_request)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    application.add_error_handler(error_handler)
    return application
