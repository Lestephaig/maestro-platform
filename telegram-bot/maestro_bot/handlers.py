import logging

from telegram import BotCommand, Chat, Update
from telegram.ext import ContextTypes

from .config import BotSettings
from .link_client import complete_account_link

logger = logging.getLogger(__name__)


def _settings(context: ContextTypes.DEFAULT_TYPE) -> BotSettings:
    return context.bot_data['settings']


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if message is None:
        return

    if not context.args:
        await message.reply_text(
            'Добро пожаловать в Maestro! 🎶\n\n'
            'Чтобы привязать Telegram, откройте настройки профиля на сайте Maestro.'
        )
        logger.info(
            'telegram_start_handled',
            extra={'event': 'telegram_start_handled', 'has_deep_link': False},
        )
        return

    chat = update.effective_chat
    if len(context.args) != 1:
        await message.reply_text('Ссылка для привязки недействительна. Создайте новую в настройках Maestro.')
        return
    if chat is None or chat.type != Chat.PRIVATE:
        await message.reply_text('Привязать аккаунт можно только в личном чате с ботом.')
        return

    result = await complete_account_link(_settings(context), context.args[0], chat.id)
    replies = {
        'linked': 'Telegram успешно привязан к вашему аккаунту Maestro.',
        'invalid_token': 'Ссылка для привязки недействительна. Создайте новую в настройках Maestro.',
        'expired_token': 'Срок действия ссылки истёк. Создайте новую в настройках Maestro.',
        'used_token': 'Эта ссылка уже была использована. Создайте новую в настройках Maestro.',
        'chat_id_conflict': 'Этот Telegram уже привязан к другому аккаунту Maestro.',
        'invalid_request': 'Не удалось обработать ссылку. Создайте новую в настройках Maestro.',
        'service_unavailable': 'Сервис Maestro временно недоступен. Попробуйте позже.',
    }
    await message.reply_text(replies[result])

    logger.info(
        'telegram_start_handled',
        extra={
            'event': 'telegram_start_handled',
            'has_deep_link': True,
            'link_result': result,
        },
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
