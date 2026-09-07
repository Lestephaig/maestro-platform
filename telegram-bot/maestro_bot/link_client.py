import logging

import httpx

from .config import BotSettings

logger = logging.getLogger(__name__)


async def complete_account_link(
    settings: BotSettings,
    token: str,
    telegram_chat_id: int,
    *,
    client=None,
) -> str:
    owns_client = client is None
    client = client or httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=settings.connect_timeout,
            read=settings.read_timeout,
            write=settings.write_timeout,
            pool=settings.pool_timeout,
        )
    )
    try:
        response = await client.post(
            f'{settings.maestro_base_url}/accounts/api/telegram/link/complete/',
            headers={'Authorization': f'Bearer {settings.maestro_api_token}'},
            json={'token': token, 'telegram_chat_id': telegram_chat_id},
        )
        payload = response.json()
        status = payload.get('status')
        if not isinstance(status, str):
            raise ValueError('Missing status in Maestro response')
    except (httpx.HTTPError, ValueError):
        logger.warning(
            'maestro_link_request_failed',
            extra={'event': 'maestro_link_request_failed'},
        )
        return 'service_unavailable'
    finally:
        if owns_client:
            await client.aclose()

    known_statuses = {
        'linked',
        'invalid_token',
        'expired_token',
        'used_token',
        'chat_id_conflict',
        'invalid_request',
        'service_unavailable',
    }
    if status not in known_statuses:
        logger.warning(
            'maestro_link_response_unknown',
            extra={'event': 'maestro_link_response_unknown'},
        )
        return 'service_unavailable'
    return status
