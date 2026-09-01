import json
import logging
import os
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

from telegram.error import NetworkError

from maestro_bot.config import BotSettings, ConfigurationError, load_settings
from maestro_bot.handlers import help_command, start_command, unknown_command
from maestro_bot.logging_config import SafeJsonFormatter
from maestro_bot.service import TelegramButton, send_telegram_message

SETTINGS = BotSettings(
    token='123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi',
    name='MaestroTestBot',
    maestro_base_url='https://maestro.test',
)


def make_update():
    message = SimpleNamespace(reply_text=AsyncMock())
    return SimpleNamespace(effective_message=message), message


class TelegramHandlerTests(IsolatedAsyncioTestCase):
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

    async def test_help_describes_bot(self):
        update, message = make_update()
        context = SimpleNamespace(bot_data={'settings': SETTINGS})

        await help_command(update, context)

        reply = message.reply_text.await_args.args[0]
        self.assertIn('@MaestroTestBot', reply)
        self.assertIn('/start', reply)
        self.assertIn('https://maestro.test', reply)

    async def test_unknown_command_returns_clear_answer(self):
        update, message = make_update()

        await unknown_command(update, SimpleNamespace())

        self.assertIn('/help', message.reply_text.await_args.args[0])


class TelegramMessageServiceTests(IsolatedAsyncioTestCase):
    async def test_sends_message_with_inline_button(self):
        bot = SimpleNamespace(send_message=AsyncMock())
        buttons = [[TelegramButton('Открыть Maestro', 'https://maestro.test')]]

        result = await send_telegram_message(
            SETTINGS, 12345, 'Тест', buttons, bot=bot
        )

        self.assertTrue(result)
        call = bot.send_message.await_args.kwargs
        self.assertEqual(call['chat_id'], 12345)
        self.assertEqual(call['text'], 'Тест')
        self.assertEqual(call['reply_markup'].inline_keyboard[0][0].text, 'Открыть Maestro')
        self.assertEqual(call['reply_markup'].inline_keyboard[0][0].url, 'https://maestro.test')

    async def test_telegram_api_error_does_not_escape(self):
        bot = SimpleNamespace(send_message=AsyncMock(side_effect=NetworkError('unavailable')))

        result = await send_telegram_message(SETTINGS, 12345, 'Тест', bot=bot)

        self.assertFalse(result)


class TelegramConfigurationTests(TestCase):
    def test_loads_own_environment(self):
        environment = {
            'TELEGRAM_BOT_TOKEN': SETTINGS.token,
            'TELEGRAM_BOT_NAME': '@MaestroTestBot',
            'MAESTRO_BASE_URL': 'https://maestro.test/',
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = load_settings()

        self.assertEqual(settings.name, 'MaestroTestBot')
        self.assertEqual(settings.maestro_base_url, 'https://maestro.test')

    def test_rejects_missing_required_environment(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationError):
                load_settings()


class TelegramLoggingTests(TestCase):
    def test_formatter_does_not_include_message_or_token(self):
        record = logging.LogRecord(
            name='maestro_bot.test',
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg='secret-token and full user message',
            args=(),
            exc_info=None,
        )
        record.event = 'safe_event'

        payload = json.loads(SafeJsonFormatter().format(record))

        self.assertEqual(payload['event'], 'safe_event')
        self.assertNotIn('secret-token', json.dumps(payload))
