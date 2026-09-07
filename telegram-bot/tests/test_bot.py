import asyncio
import json
import logging
import os
import sqlite3
import tempfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import AsyncMock, patch

from aiohttp.test_utils import TestClient, TestServer
from telegram.error import BadRequest, NetworkError, RetryAfter

from maestro_bot.application import build_application
from maestro_bot.config import BotSettings, ConfigurationError, load_settings
from maestro_bot.delivery_api import create_delivery_app
from maestro_bot.handlers import help_command, start_command, unknown_command
from maestro_bot.idempotency import IdempotencyStore
from maestro_bot.link_client import complete_account_link
from maestro_bot.logging_config import SafeJsonFormatter
from maestro_bot.service import (
    TelegramButton,
    TelegramSendResult,
    send_telegram_message,
)

SETTINGS = BotSettings(
    token='123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi',
    name='MaestroTestBot',
    maestro_base_url='https://maestro.test',
    maestro_api_token='test-platform-api-token',
    delivery_api_token='test-delivery-api-token',
)


def make_update(chat_type='private'):
    message = SimpleNamespace(reply_text=AsyncMock())
    chat = SimpleNamespace(id=12345, type=chat_type)
    return SimpleNamespace(effective_message=message, effective_chat=chat), message


class TelegramHandlerTests(IsolatedAsyncioTestCase):
    async def test_start_returns_welcome_without_deep_link(self):
        update, message = make_update()

        await start_command(update, SimpleNamespace(args=[]))

        reply = message.reply_text.await_args.args[0]
        self.assertIn('Добро пожаловать', reply)
        self.assertNotIn('Параметр ссылки', reply)

    @patch('maestro_bot.handlers.complete_account_link', new_callable=AsyncMock)
    async def test_start_links_deep_link_without_echoing_it(self, complete_link):
        update, message = make_update()
        secret_parameter = 'secret-deep-link-value'
        complete_link.return_value = 'linked'
        context = SimpleNamespace(args=[secret_parameter], bot_data={'settings': SETTINGS})

        await start_command(update, context)

        reply = message.reply_text.await_args.args[0]
        self.assertIn('успешно привязан', reply)
        self.assertNotIn(secret_parameter, reply)
        complete_link.assert_awaited_once_with(SETTINGS, secret_parameter, 12345)

    @patch('maestro_bot.handlers.complete_account_link', new_callable=AsyncMock)
    async def test_start_explains_expired_link(self, complete_link):
        update, message = make_update()
        complete_link.return_value = 'expired_token'

        await start_command(
            update,
            SimpleNamespace(args=['expired'], bot_data={'settings': SETTINGS}),
        )

        self.assertIn('истёк', message.reply_text.await_args.args[0])

    @patch('maestro_bot.handlers.complete_account_link', new_callable=AsyncMock)
    async def test_start_rejects_linking_from_group(self, complete_link):
        update, message = make_update(chat_type='group')

        await start_command(
            update,
            SimpleNamespace(args=['secret'], bot_data={'settings': SETTINGS}),
        )

        self.assertIn('личном чате', message.reply_text.await_args.args[0])
        complete_link.assert_not_awaited()

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
        bot = SimpleNamespace(
            send_message=AsyncMock(return_value=SimpleNamespace(message_id=321))
        )
        buttons = [[TelegramButton('Открыть Maestro', 'https://maestro.test')]]

        result = await send_telegram_message(
            SETTINGS, 12345, 'Тест', buttons, parse_mode='HTML', bot=bot
        )

        self.assertTrue(result)
        call = bot.send_message.await_args.kwargs
        self.assertEqual(call['chat_id'], 12345)
        self.assertEqual(call['text'], 'Тест')
        self.assertEqual(call['parse_mode'], 'HTML')
        self.assertEqual(call['reply_markup'].inline_keyboard[0][0].text, 'Открыть Maestro')
        self.assertEqual(call['reply_markup'].inline_keyboard[0][0].url, 'https://maestro.test')

    async def test_telegram_api_error_does_not_escape(self):
        bot = SimpleNamespace(send_message=AsyncMock(side_effect=NetworkError('unavailable')))

        result = await send_telegram_message(SETTINGS, 12345, 'Тест', bot=bot)

        self.assertFalse(result)

    async def test_classifies_permanent_and_rate_limit_errors(self):
        cases = (
            (BadRequest('bad recipient'), 'rejected'),
            (RetryAfter(3), 'rate_limited'),
        )
        for error, expected in cases:
            with self.subTest(error=type(error).__name__):
                bot = SimpleNamespace(send_message=AsyncMock(side_effect=error))
                result = await send_telegram_message(
                    SETTINGS, 12345, 'Тест', bot=bot
                )
                self.assertFalse(result)
                self.assertEqual(result.error_kind, expected)


class TelegramDeliveryApiTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temporary_directory.name) / 'idempotency.sqlite3'
        self.settings = replace(SETTINGS, delivery_db_path=str(self.db_path))
        self.bot = SimpleNamespace(
            send_message=AsyncMock(return_value=SimpleNamespace(message_id=4321))
        )
        self.store = IdempotencyStore(self.db_path)
        await self.store.initialize()
        app = create_delivery_app(self.settings, self.bot, self.store)
        self.client = TestClient(TestServer(app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.temporary_directory.cleanup()

    def _headers(self, key='notification-delivery-7', token=None):
        return {
            'Authorization': f'Bearer {token or self.settings.delivery_api_token}',
            'Idempotency-Key': key,
        }

    def _payload(self, **changes):
        payload = {
            'chat_id': 123456789,
            'text': 'Новое <b>сообщение</b>',
            'parse_mode': 'HTML',
            'buttons': [[{
                'text': 'Открыть',
                'url': 'https://maestro.test/chat/7/',
            }]],
        }
        payload.update(changes)
        return payload

    async def test_health_endpoint_has_no_configuration_data(self):
        response = await self.client.get('/healthz')

        self.assertEqual(response.status, 200)
        self.assertEqual(await response.json(), {'ok': True})

    async def test_rejects_missing_and_wrong_authorization_before_send(self):
        for headers in ({}, self._headers(token='wrong-token')):
            with self.subTest(headers=bool(headers)):
                response = await self.client.post(
                    '/internal/v1/telegram/messages',
                    json=self._payload(),
                    headers=headers,
                )
                self.assertEqual(response.status, 401)
        self.bot.send_message.assert_not_awaited()

    async def test_rejects_malformed_json_and_invalid_fields(self):
        response = await self.client.post(
            '/internal/v1/telegram/messages',
            data='{',
            headers={**self._headers(), 'Content-Type': 'application/json'},
        )
        self.assertEqual(response.status, 400)

        invalid_payloads = (
            self._payload(chat_id=0),
            self._payload(parse_mode='Markdown'),
            self._payload(buttons=[[{'text': 'Открыть', 'url': 'http://unsafe.test'}]]),
        )
        for index, payload in enumerate(invalid_payloads, start=1):
            with self.subTest(index=index):
                response = await self.client.post(
                    '/internal/v1/telegram/messages',
                    json=payload,
                    headers=self._headers(f'notification-delivery-{index + 10}'),
                )
                self.assertEqual(response.status, 400)
        self.bot.send_message.assert_not_awaited()

    async def test_rejects_oversized_request(self):
        response = await self.client.post(
            '/internal/v1/telegram/messages',
            data=b'x' * (17 * 1024),
            headers={**self._headers(), 'Content-Type': 'application/json'},
        )

        self.assertEqual(response.status, 413)
        self.bot.send_message.assert_not_awaited()

    async def test_sends_html_buttons_and_deduplicates_success(self):
        first = await self.client.post(
            '/internal/v1/telegram/messages',
            json=self._payload(),
            headers=self._headers(),
        )
        second = await self.client.post(
            '/internal/v1/telegram/messages',
            json=self._payload(),
            headers=self._headers(),
        )

        self.assertEqual(first.status, 200)
        self.assertEqual(await first.json(), {
            'ok': True,
            'telegram_message_id': 4321,
            'duplicate': False,
        })
        self.assertEqual(second.status, 200)
        self.assertTrue((await second.json())['duplicate'])
        self.bot.send_message.assert_awaited_once()
        call = self.bot.send_message.await_args.kwargs
        self.assertEqual(call['chat_id'], 123456789)
        self.assertEqual(call['parse_mode'], 'HTML')
        self.assertEqual(call['reply_markup'].inline_keyboard[0][0].url, 'https://maestro.test/chat/7/')

        reopened_store = IdempotencyStore(self.db_path)
        await reopened_store.initialize()
        persisted_claim = await reopened_store.claim('notification-delivery-7')
        self.assertEqual(persisted_claim.state, 'duplicate')
        self.assertEqual(persisted_claim.telegram_message_id, 4321)

        database_bytes = self.db_path.read_bytes()
        self.assertNotIn(b'notification-delivery-7', database_bytes)
        self.assertNotIn('123456789'.encode(), database_bytes)
        self.assertNotIn('сообщение'.encode(), database_bytes)
        with sqlite3.connect(self.db_path) as connection:
            row = connection.execute(
                'SELECT status, telegram_message_id FROM telegram_deliveries'
            ).fetchone()
        self.assertEqual(row, ('succeeded', 4321))

    @patch('maestro_bot.delivery_api.send_telegram_message', new_callable=AsyncMock)
    async def test_maps_telegram_errors_to_contract_statuses(self, send_message):
        cases = (
            ('rejected', 422),
            ('rate_limited', 429),
            ('temporary', 502),
            ('service_unavailable', 503),
        )
        for index, (kind, expected_status) in enumerate(cases, start=20):
            with self.subTest(kind=kind):
                send_message.return_value = TelegramSendResult(False, error_kind=kind)
                response = await self.client.post(
                    '/internal/v1/telegram/messages',
                    json=self._payload(),
                    headers=self._headers(f'notification-delivery-{index}'),
                )
                self.assertEqual(response.status, expected_status)

    @patch('maestro_bot.delivery_api.send_telegram_message', new_callable=AsyncMock)
    async def test_concurrent_key_is_never_sent_twice(self, send_message):
        started = asyncio.Event()
        finish = asyncio.Event()

        async def delayed_send(*args, **kwargs):
            started.set()
            await finish.wait()
            return TelegramSendResult(True, message_id=99)

        send_message.side_effect = delayed_send
        first_task = asyncio.create_task(self.client.post(
            '/internal/v1/telegram/messages',
            json=self._payload(),
            headers=self._headers('notification-delivery-99'),
        ))
        await started.wait()
        second = await self.client.post(
            '/internal/v1/telegram/messages',
            json=self._payload(),
            headers=self._headers('notification-delivery-99'),
        )
        finish.set()
        first = await first_task

        self.assertEqual(first.status, 200)
        self.assertEqual(second.status, 503)
        send_message.assert_awaited_once()

    async def test_logs_do_not_contain_secrets_or_personal_data(self):
        with self.assertLogs('maestro_bot', level='INFO') as logs:
            response = await self.client.post(
                '/internal/v1/telegram/messages',
                json=self._payload(),
                headers=self._headers(token='bad-secret-token'),
            )

        self.assertEqual(response.status, 401)
        rendered = '\n'.join(logs.output)
        self.assertNotIn('bad-secret-token', rendered)
        self.assertNotIn('123456789', rendered)
        self.assertNotIn('сообщение', rendered)

    async def test_success_records_older_than_seven_days_are_cleaned(self):
        key = 'notification-delivery-700'
        self.assertEqual((await self.store.claim(key)).state, 'claimed')
        await self.store.complete(key, 700)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                'UPDATE telegram_deliveries SET processed_at = 0 WHERE telegram_message_id = 700'
            )

        claim = await self.store.claim(key)

        self.assertEqual(claim.state, 'claimed')


class TelegramApplicationLifecycleTests(IsolatedAsyncioTestCase):
    @patch('maestro_bot.application.DeliveryApiServer')
    async def test_http_api_starts_and_stops_with_bot(self, server_class):
        server = server_class.return_value
        server.start = AsyncMock()
        server.stop = AsyncMock()
        with tempfile.TemporaryDirectory() as directory:
            heartbeat = Path(directory) / 'heartbeat'
            application = build_application(SETTINGS, heartbeat)
            with patch(
                'telegram.ext.ExtBot.set_my_commands',
                new=AsyncMock(),
            ):
                await application.post_init(application)
                await application.post_shutdown(application)

        server_class.assert_called_once_with(SETTINGS, application.bot)
        server.start.assert_awaited_once()
        server.stop.assert_awaited_once()
        self.assertFalse(heartbeat.exists())


class MaestroLinkClientTests(IsolatedAsyncioTestCase):
    async def test_sends_link_to_authenticated_platform_endpoint(self):
        response = SimpleNamespace(json=lambda: {'status': 'linked'})
        client = SimpleNamespace(post=AsyncMock(return_value=response))

        result = await complete_account_link(
            SETTINGS,
            'one-time-token',
            12345,
            client=client,
        )

        self.assertEqual(result, 'linked')
        call = client.post.await_args
        self.assertEqual(
            call.args[0],
            'https://maestro.test/accounts/api/telegram/link/complete/',
        )
        self.assertEqual(
            call.kwargs['headers']['Authorization'],
            'Bearer test-platform-api-token',
        )
        self.assertEqual(call.kwargs['json']['telegram_chat_id'], 12345)


class TelegramConfigurationTests(TestCase):
    def test_loads_own_environment(self):
        environment = {
            'TELEGRAM_BOT_TOKEN': SETTINGS.token,
            'TELEGRAM_BOT_NAME': '@MaestroTestBot',
            'MAESTRO_BASE_URL': 'https://maestro.test/',
            'MAESTRO_API_TOKEN': 'test-platform-api-token',
            'TELEGRAM_DELIVERY_API_TOKEN': 'test-delivery-api-token',
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = load_settings()

        self.assertEqual(settings.name, 'MaestroTestBot')
        self.assertEqual(settings.maestro_base_url, 'https://maestro.test')
        self.assertEqual(settings.delivery_api_port, 8080)

    def test_rejects_reused_link_and_delivery_secret(self):
        environment = {
            'TELEGRAM_BOT_TOKEN': SETTINGS.token,
            'TELEGRAM_BOT_NAME': 'MaestroTestBot',
            'MAESTRO_BASE_URL': 'https://maestro.test',
            'MAESTRO_API_TOKEN': 'same-token',
            'TELEGRAM_DELIVERY_API_TOKEN': 'same-token',
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaises(ConfigurationError):
                load_settings()

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
