import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from urllib.parse import urlencode

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import TelegramConnection, TelegramLinkToken, User

TOKEN_TTL = timedelta(minutes=15)
RATE_LIMIT_WINDOW = timedelta(minutes=15)
RATE_LIMIT_COUNT = 5


class TelegramLinkRateLimited(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__('Telegram link token creation rate limit exceeded')


class TelegramLinkResult(str, Enum):
    LINKED = 'linked'
    INVALID_TOKEN = 'invalid_token'
    EXPIRED_TOKEN = 'expired_token'
    USED_TOKEN = 'used_token'
    CHAT_ID_CONFLICT = 'chat_id_conflict'


@dataclass(frozen=True)
class TelegramLink:
    url: str
    expires_at: datetime


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


@transaction.atomic
def create_telegram_link(user, bot_name: str) -> TelegramLink:
    now = timezone.now()
    window_start = now - RATE_LIMIT_WINDOW
    User.objects.select_for_update().get(pk=user.pk)
    recent_tokens = list(
        TelegramLinkToken.objects.select_for_update()
        .filter(user=user, created_at__gte=window_start)
        .order_by('created_at')
    )
    if len(recent_tokens) >= RATE_LIMIT_COUNT:
        retry_at = recent_tokens[0].created_at + RATE_LIMIT_WINDOW
        retry_after = max(1, int((retry_at - now).total_seconds()) + 1)
        raise TelegramLinkRateLimited(retry_after)

    TelegramLinkToken.objects.filter(
        user=user,
        used_at__isnull=True,
        expires_at__gt=now,
    ).update(expires_at=now)

    expires_at = now + TOKEN_TTL
    for _ in range(3):
        raw_token = secrets.token_urlsafe(32)
        try:
            with transaction.atomic():
                TelegramLinkToken.objects.create(
                    user=user,
                    token_hash=_hash_token(raw_token),
                    expires_at=expires_at,
                )
            break
        except IntegrityError:
            continue
    else:
        raise RuntimeError('Could not generate a unique Telegram link token')

    query = urlencode({'start': raw_token})
    return TelegramLink(
        url=f'https://t.me/{bot_name}?{query}',
        expires_at=expires_at,
    )


@transaction.atomic
def consume_telegram_link(raw_token: str, telegram_chat_id: int) -> TelegramLinkResult:
    token_hash = _hash_token(raw_token)
    link_token = (
        TelegramLinkToken.objects.select_for_update()
        .select_related('user')
        .filter(token_hash=token_hash)
        .first()
    )
    if link_token is None:
        return TelegramLinkResult.INVALID_TOKEN
    if link_token.used_at is not None:
        return TelegramLinkResult.USED_TOKEN

    now = timezone.now()
    if link_token.expires_at <= now:
        return TelegramLinkResult.EXPIRED_TOKEN

    # Every valid token is consumed by its first attempt, including a chat-id conflict.
    link_token.used_at = now
    link_token.save(update_fields=['used_at'])

    connection = (
        TelegramConnection.objects.select_for_update()
        .filter(user=link_token.user)
        .first()
    )
    conflict_exists = (
        TelegramConnection.objects.select_for_update()
        .filter(telegram_chat_id=telegram_chat_id)
        .exclude(user=link_token.user)
        .exists()
    )
    if conflict_exists:
        return TelegramLinkResult.CHAT_ID_CONFLICT

    try:
        with transaction.atomic():
            if connection is None:
                TelegramConnection.objects.create(
                    user=link_token.user,
                    telegram_chat_id=telegram_chat_id,
                    linked_at=now,
                )
            else:
                connection.telegram_chat_id = telegram_chat_id
                connection.linked_at = now
                connection.save(update_fields=['telegram_chat_id', 'linked_at', 'updated_at'])
    except IntegrityError:
        # Covers a concurrent attempt to bind the same Telegram chat.
        return TelegramLinkResult.CHAT_ID_CONFLICT

    # A successful explicit link opts the user into Telegram chat notifications.
    # Import locally to keep the accounts models independent from notifications.
    from notifications.models import Notification, NotificationPreference

    preference = NotificationPreference.get_or_create_for(
        link_token.user,
        Notification.NOTIFICATION_TYPE_CHAT_MESSAGE,
    )
    if not preference.telegram_enabled:
        preference.telegram_enabled = True
        preference.save(update_fields=['telegram_enabled', 'updated_at'])

    return TelegramLinkResult.LINKED
