import json
import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings
from telegram.error import NetworkError

from .handlers import help_command, start_command, unknown_command
from .logging import TelegramJsonFormatter
from .service import TelegramButton, send_telegram_message


def make_update():
    message = SimpleNamespace(reply_text=AsyncMock())
    return SimpleNamespace(effective_message=message), message


class TelegramHandlerTests(SimpleTestCase):
    async def test_start_returns_welcome_without_deep_link(self):
        update, message = make_update()

        await start_command(update, SimpleNamespace(args=[]))

        reply = message.reply_text.await_args.args[0]
        self.assertIn('Добро пожаловать', reply)
        self.assertNotIn('Параметр ссылки', reply)

    async def test_start_acknowledges_deep_link_without_echoing_it(self):
        update, message = make_update()
        secret_parameter = 'secret-deep-link-value'

        await start_command(update, SimpleNamespace(args=[secret_parameter]))

        reply = message.reply_text.await_args.args[0]
        self.assertIn('Параметр ссылки получен', reply)
        self.assertNotIn(secret_parameter, reply)

    @override_settings(TELEGRAM_BOT_NAME='MaestroTestBot', MAESTRO_BASE_URL='https://maestro.test')
    async def test_help_describes_bot(self):
        update, message = make_update()

        await help_command(update, SimpleNamespace())

        reply = message.reply_text.await_args.args[0]
        self.assertIn('@MaestroTestBot', reply)
        self.assertIn('/start', reply)
        self.assertIn('https://maestro.test', reply)

    async def test_unknown_command_returns_clear_answer(self):
        update, message = make_update()

        await unknown_command(update, SimpleNamespace())

        self.assertIn('/help', message.reply_text.await_args.args[0])


class TelegramMessageServiceTests(SimpleTestCase):
    async def test_sends_message_with_inline_button(self):
        bot = SimpleNamespace(send_message=AsyncMock())
        buttons = [[TelegramButton('Открыть Maestro', 'https://maestro.test')]]

        result = await send_telegram_message(12345, 'Тест', buttons, bot=bot)

        self.assertTrue(result)
        call = bot.send_message.await_args.kwargs
        self.assertEqual(call['chat_id'], 12345)
        self.assertEqual(call['text'], 'Тест')
        self.assertEqual(call['reply_markup'].inline_keyboard[0][0].text, 'Открыть Maestro')
        self.assertEqual(call['reply_markup'].inline_keyboard[0][0].url, 'https://maestro.test')

    async def test_telegram_api_error_does_not_escape(self):
        bot = SimpleNamespace(send_message=AsyncMock(side_effect=NetworkError('unavailable')))

        result = await send_telegram_message(12345, 'Тест', bot=bot)

        self.assertFalse(result)


class TelegramSafetyTests(SimpleTestCase):
    def test_structured_formatter_does_not_include_log_message(self):
        record = logging.LogRecord(
            name='telegram_bot.test',
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg='secret-token and full user message',
            args=(),
            exc_info=None,
        )
        record.event = 'safe_event'

        payload = json.loads(TelegramJsonFormatter().format(record))

        self.assertEqual(payload['event'], 'safe_event')
        self.assertNotIn('secret-token', json.dumps(payload))

    @override_settings(TELEGRAM_BOT_TOKEN='')
    def test_run_command_requires_token(self):
        with self.assertRaisesMessage(CommandError, 'TELEGRAM_BOT_TOKEN is required'):
            call_command('run_telegram_bot')

    @override_settings(TELEGRAM_BOT_TOKEN='')
    async def test_missing_token_returns_false(self):
        result = await send_telegram_message(12345, 'Тест')

        self.assertFalse(result)
