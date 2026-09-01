import logging
from dataclasses import dataclass
from typing import Sequence

from asgiref.sync import async_to_sync
from django.conf import settings
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from telegram.request import HTTPXRequest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelegramButton:
    text: str
    url: str


ButtonRows = Sequence[Sequence[TelegramButton]]


def _build_keyboard(buttons: ButtonRows | None):
    if not buttons:
        return None
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(button.text, url=button.url) for button in row]
        for row in buttons
    ])


def _make_bot():
    request = HTTPXRequest(
        connect_timeout=settings.TELEGRAM_CONNECT_TIMEOUT,
        read_timeout=settings.TELEGRAM_READ_TIMEOUT,
        write_timeout=settings.TELEGRAM_WRITE_TIMEOUT,
        pool_timeout=settings.TELEGRAM_POOL_TIMEOUT,
    )
    return Bot(token=settings.TELEGRAM_BOT_TOKEN, request=request)


async def send_telegram_message(chat_id, text: str, buttons: ButtonRows | None = None, *, bot=None):
    """Send one message without leaking its content or recipient into logs."""
    if not settings.TELEGRAM_BOT_TOKEN and bot is None:
        logger.error(
            'telegram_not_configured',
            extra={'event': 'telegram_not_configured'},
        )
        return False

    keyboard = _build_keyboard(buttons)
    owns_bot = bot is None
    bot = bot or _make_bot()
    try:
        if owns_bot:
            async with bot:
                await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
        else:
            await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    except (TelegramError, TimeoutError) as error:
        logger.warning(
            'telegram_send_failed',
            extra={
                'event': 'telegram_send_failed',
                'error_type': type(error).__name__,
                'button_count': sum(len(row) for row in buttons or ()),
            },
        )
        return False
    except Exception as error:
        logger.error(
            'telegram_send_unexpected_error',
            extra={
                'event': 'telegram_send_unexpected_error',
                'error_type': type(error).__name__,
                'button_count': sum(len(row) for row in buttons or ()),
            },
        )
        return False

    logger.info(
        'telegram_message_sent',
        extra={
            'event': 'telegram_message_sent',
            'button_count': sum(len(row) for row in buttons or ()),
        },
    )
    return True


def send_telegram_message_sync(chat_id, text: str, buttons: ButtonRows | None = None):
    """Synchronous adapter for regular Django views, signals and commands."""
    return async_to_sync(send_telegram_message)(chat_id, text, buttons)
