import hmac
import json
import logging
import re
from urllib.parse import urlsplit

from aiohttp import web

from .idempotency import IdempotencyStore
from .service import TelegramButton, send_telegram_message

logger = logging.getLogger(__name__)

MAX_REQUEST_BODY_BYTES = 16 * 1024
MAX_TEXT_LENGTH = 4096
MAX_BUTTON_ROWS = 8
MAX_BUTTONS_PER_ROW = 8
MAX_BUTTON_TEXT_LENGTH = 64
MAX_BUTTON_URL_LENGTH = 2048
IDEMPOTENCY_KEY_PATTERN = re.compile(r'^[A-Za-z0-9._:-]{1,200}$')


def _json_response(status, error):
    return web.json_response({'ok': False, 'error': error}, status=status)


def _is_authorized(request, expected_token):
    authorization = request.headers.get('Authorization', '')
    if not authorization.startswith('Bearer '):
        return False
    supplied_token = authorization[7:]
    return bool(supplied_token) and hmac.compare_digest(supplied_token, expected_token)


def _validate_https_url(value):
    if not isinstance(value, str) or not value or len(value) > MAX_BUTTON_URL_LENGTH:
        return False
    parsed = urlsplit(value)
    return (
        parsed.scheme == 'https'
        and bool(parsed.netloc)
        and parsed.username is None
        and parsed.password is None
    )


def validate_message_payload(payload):
    if not isinstance(payload, dict):
        raise ValueError('payload_not_object')
    if set(payload) != {'chat_id', 'text', 'parse_mode', 'buttons'}:
        raise ValueError('payload_fields')

    chat_id = payload['chat_id']
    if not isinstance(chat_id, int) or isinstance(chat_id, bool) or chat_id <= 0:
        raise ValueError('chat_id')

    text = payload['text']
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT_LENGTH:
        raise ValueError('text')
    if payload['parse_mode'] != 'HTML':
        raise ValueError('parse_mode')

    raw_rows = payload['buttons']
    if not isinstance(raw_rows, list) or len(raw_rows) > MAX_BUTTON_ROWS:
        raise ValueError('buttons')
    buttons = []
    total_buttons = 0
    for raw_row in raw_rows:
        if (
            not isinstance(raw_row, list)
            or not raw_row
            or len(raw_row) > MAX_BUTTONS_PER_ROW
        ):
            raise ValueError('button_row')
        row = []
        for raw_button in raw_row:
            if not isinstance(raw_button, dict) or set(raw_button) != {'text', 'url'}:
                raise ValueError('button')
            label = raw_button['text']
            if (
                not isinstance(label, str)
                or not label.strip()
                or len(label) > MAX_BUTTON_TEXT_LENGTH
                or not _validate_https_url(raw_button['url'])
            ):
                raise ValueError('button')
            row.append(TelegramButton(label, raw_button['url']))
        buttons.append(row)
        total_buttons += len(row)
    if total_buttons > MAX_BUTTON_ROWS * MAX_BUTTONS_PER_ROW:
        raise ValueError('buttons')
    return chat_id, text, buttons


@web.middleware
async def request_error_middleware(request, handler):
    try:
        return await handler(request)
    except web.HTTPRequestEntityTooLarge:
        logger.warning('delivery_payload_too_large', extra={'event': 'delivery_payload_too_large'})
        return _json_response(413, 'payload_too_large')


def create_delivery_app(settings, bot, store):
    async def healthz(request):
        del request
        return web.json_response({'ok': True})

    async def send_message(request):
        if not _is_authorized(request, settings.delivery_api_token):
            logger.warning(
                'delivery_unauthorized',
                extra={'event': 'delivery_unauthorized'},
            )
            return _json_response(401, 'unauthorized')

        idempotency_key = request.headers.get('Idempotency-Key', '')
        if not IDEMPOTENCY_KEY_PATTERN.fullmatch(idempotency_key):
            return _json_response(400, 'invalid_idempotency_key')
        if request.content_type != 'application/json':
            return _json_response(400, 'invalid_content_type')

        try:
            payload = await request.json(loads=json.loads)
            chat_id, text, buttons = validate_message_payload(payload)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError):
            return _json_response(400, 'invalid_payload')

        try:
            claim = await store.claim(idempotency_key)
        except Exception as error:
            logger.error(
                'delivery_store_unavailable',
                extra={
                    'event': 'delivery_store_unavailable',
                    'error_type': type(error).__name__,
                },
            )
            return _json_response(503, 'service_unavailable')
        if claim.state == 'duplicate':
            return web.json_response({
                'ok': True,
                'telegram_message_id': claim.telegram_message_id,
                'duplicate': True,
            })
        if claim.state == 'processing':
            return _json_response(503, 'request_in_progress')

        result = await send_telegram_message(
            settings,
            chat_id,
            text,
            buttons,
            parse_mode=payload['parse_mode'],
            bot=bot,
        )
        if not result:
            try:
                await store.release(idempotency_key)
            except Exception as error:
                logger.error(
                    'delivery_store_release_failed',
                    extra={
                        'event': 'delivery_store_release_failed',
                        'error_type': type(error).__name__,
                    },
                )
            statuses = {
                'rejected': (422, 'telegram_rejected'),
                'rate_limited': (429, 'telegram_rate_limited'),
                'temporary': (502, 'telegram_unavailable'),
                'service_unavailable': (503, 'service_unavailable'),
            }
            status, code = statuses.get(
                result.error_kind,
                (503, 'service_unavailable'),
            )
            return _json_response(status, code)

        try:
            await store.complete(idempotency_key, result.message_id)
        except Exception as error:
            logger.error(
                'delivery_result_persistence_failed',
                extra={
                    'event': 'delivery_result_persistence_failed',
                    'error_type': type(error).__name__,
                },
            )
            return _json_response(503, 'result_persistence_failed')

        return web.json_response({
            'ok': True,
            'telegram_message_id': result.message_id,
            'duplicate': False,
        })

    app = web.Application(
        client_max_size=MAX_REQUEST_BODY_BYTES,
        middlewares=(request_error_middleware,),
    )
    app.router.add_get('/healthz', healthz)
    app.router.add_post('/internal/v1/telegram/messages', send_message)
    return app


class DeliveryApiServer:
    def __init__(self, settings, bot):
        self.settings = settings
        self.store = IdempotencyStore(settings.delivery_db_path)
        self.runner = web.AppRunner(create_delivery_app(settings, bot, self.store))

    async def start(self):
        await self.store.initialize()
        await self.runner.setup()
        site = web.TCPSite(
            self.runner,
            self.settings.delivery_api_host,
            self.settings.delivery_api_port,
        )
        await site.start()
        logger.info('delivery_api_started', extra={'event': 'delivery_api_started'})

    async def stop(self):
        await self.runner.cleanup()
        logger.info('delivery_api_stopped', extra={'event': 'delivery_api_stopped'})
