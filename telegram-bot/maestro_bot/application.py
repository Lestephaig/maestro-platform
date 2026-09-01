import asyncio
import logging
from contextlib import suppress
from pathlib import Path

from telegram.error import TelegramError
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest

from .config import BotSettings
from .handlers import BOT_COMMANDS, error_handler, help_command, start_command, unknown_command

logger = logging.getLogger(__name__)
HEARTBEAT_FILE = Path('/tmp/maestro-telegram-bot.heartbeat')


async def _heartbeat(path: Path):
    while True:
        path.touch()
        await asyncio.sleep(30)


def build_application(settings: BotSettings, heartbeat_file: Path = HEARTBEAT_FILE):
    async def post_init(application: Application):
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
        application.bot_data['heartbeat_task'] = asyncio.create_task(
            _heartbeat(heartbeat_file)
        )
        logger.info('telegram_bot_started', extra={'event': 'telegram_bot_started'})

    async def post_shutdown(application: Application):
        task = application.bot_data.pop('heartbeat_task', None)
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        heartbeat_file.unlink(missing_ok=True)
        logger.info('telegram_bot_stopped', extra={'event': 'telegram_bot_stopped'})

    api_request = HTTPXRequest(
        connect_timeout=settings.connect_timeout,
        read_timeout=settings.read_timeout,
        write_timeout=settings.write_timeout,
        pool_timeout=settings.pool_timeout,
    )
    updates_request = HTTPXRequest(
        connect_timeout=settings.connect_timeout,
        read_timeout=settings.poll_timeout + 5,
        write_timeout=settings.write_timeout,
        pool_timeout=settings.pool_timeout,
    )
    application = (
        ApplicationBuilder()
        .token(settings.token)
        .request(api_request)
        .get_updates_request(updates_request)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    application.bot_data['settings'] = settings
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    application.add_error_handler(error_handler)
    return application
