import asyncio
import logging
from dataclasses import dataclass
from typing import Sequence

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TelegramError, TimedOut
from telegram.request import HTTPXRequest

from .config import BotSettings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TelegramButton:
    text: str
    url: str


ButtonRows = Sequence[Sequence[TelegramButton]]


@dataclass(frozen=True)
class TelegramSendResult:
    ok: bool
    message_id: int | None = None
    error_kind: str | None = None

    def __bool__(self):
        return self.ok


def _build_keyboard(buttons: ButtonRows | None):
    if not buttons:
        return None
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(button.text, url=button.url) for button in row]
        for row in buttons
    ])


def _make_bot(settings: BotSettings):
    request = HTTPXRequest(
        connect_timeout=settings.connect_timeout,
        read_timeout=settings.read_timeout,
        write_timeout=settings.write_timeout,
        pool_timeout=settings.pool_timeout,
    )
    return Bot(token=settings.token, request=request)


async def send_telegram_message(
    settings: BotSettings,
    chat_id,
    text: str,
    buttons: ButtonRows | None = None,
    *,
    parse_mode: str | None = None,
    bot=None,
):
    """Send one message without leaking its content or recipient into logs."""
    keyboard = _build_keyboard(buttons)
    owns_bot = bot is None
    bot = bot or _make_bot(settings)
    try:
        if owns_bot:
            async with bot:
                sent_message = await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    reply_markup=keyboard,
                )
        else:
            sent_message = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=keyboard,
            )
    except RetryAfter as error:
        logger.warning(
            'telegram_send_failed',
            extra={
                'event': 'telegram_send_failed',
                'error_type': type(error).__name__,
                'button_count': sum(len(row) for row in buttons or ()),
            },
        )
        return TelegramSendResult(False, error_kind='rate_limited')
    except (BadRequest, Forbidden) as error:
        logger.warning(
            'telegram_send_failed',
            extra={
                'event': 'telegram_send_failed',
                'error_type': type(error).__name__,
                'button_count': sum(len(row) for row in buttons or ()),
            },
        )
        return TelegramSendResult(False, error_kind='rejected')
    except (NetworkError, TimedOut, TimeoutError, TelegramError) as error:
        logger.warning(
            'telegram_send_failed',
            extra={
                'event': 'telegram_send_failed',
                'error_type': type(error).__name__,
                'button_count': sum(len(row) for row in buttons or ()),
            },
        )
        return TelegramSendResult(False, error_kind='temporary')
    except Exception as error:
        logger.error(
            'telegram_send_unexpected_error',
            extra={
                'event': 'telegram_send_unexpected_error',
                'error_type': type(error).__name__,
                'button_count': sum(len(row) for row in buttons or ()),
            },
        )
        return TelegramSendResult(False, error_kind='service_unavailable')

    message_id = getattr(sent_message, 'message_id', None)
    if not isinstance(message_id, int) or isinstance(message_id, bool) or message_id <= 0:
        logger.error(
            'telegram_send_invalid_result',
            extra={'event': 'telegram_send_invalid_result'},
        )
        return TelegramSendResult(False, error_kind='temporary')
    logger.info(
        'telegram_message_sent',
        extra={
            'event': 'telegram_message_sent',
            'button_count': sum(len(row) for row in buttons or ()),
        },
    )
    return TelegramSendResult(True, message_id=message_id)


def send_telegram_message_sync(
    settings: BotSettings,
    chat_id,
    text: str,
    buttons: ButtonRows | None = None,
):
    """Synchronous adapter; call the async function from an active event loop."""
    return asyncio.run(send_telegram_message(settings, chat_id, text, buttons))
