import logging

from telegram import BotCommand, Update
from telegram.ext import ContextTypes

from .config import BotSettings

logger = logging.getLogger(__name__)


def _settings(context: ContextTypes.DEFAULT_TYPE) -> BotSettings:
    return context.bot_data['settings']


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message is None:
        return

    has_deep_link = bool(context.args)
    text = (
        'Добро пожаловать в Maestro! 🎶\n\n'
        'Этот бот будет помогать вам следить за событиями на платформе.'
    )
    if has_deep_link:
        text += (
            '\n\nПараметр ссылки получен. '
            'Привязка аккаунта будет добавлена на следующем этапе.'
        )

    await message.reply_text(text)
    logger.info(
        'telegram_start_handled',
        extra={'event': 'telegram_start_handled', 'has_deep_link': has_deep_link},
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message is None:
        return

    settings = _settings(context)
    await message.reply_text(
        f'@{settings.name} — бот платформы Maestro.\n\n'
        'Команды:\n'
        '/start — начать работу\n'
        '/help — показать эту справку\n\n'
        f'Сайт: {settings.maestro_base_url}'
    )
    logger.info('telegram_help_handled', extra={'event': 'telegram_help_handled'})


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    del context
    message = update.effective_message
    if message is None:
        return

    await message.reply_text(
        'Не знаю такую команду. Используйте /help, чтобы увидеть список команд.'
    )
    logger.info('telegram_unknown_command', extra={'event': 'telegram_unknown_command'})


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    del update
    error = context.error
    logger.error(
        'telegram_update_failed',
        extra={
            'event': 'telegram_update_failed',
            'error_type': type(error).__name__ if error else 'UnknownError',
        },
    )


BOT_COMMANDS = (
    BotCommand('start', 'Начать работу'),
    BotCommand('help', 'Помощь'),
)
