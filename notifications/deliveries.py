import json
import logging
from datetime import timedelta
from urllib import request as urllib_request

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import escape
from django.utils.text import Truncator

from .channels import get_active_channels
from .models import Notification, NotificationDelivery, NotificationPreference

logger = logging.getLogger(__name__)

PREVIEW_LENGTH = 160
TELEGRAM_PREVIEW_LENGTH = 50


def absolute_platform_url(path):
    return f"{settings.SITE_URL.rstrip('/')}{path}"


def get_user_display_name(user):
    if getattr(user, 'display_name', ''):
        return user.display_name
    if hasattr(user, 'performer_profile') and user.performer_profile.full_name:
        return user.performer_profile.full_name
    if hasattr(user, 'agent_profile') and user.agent_profile.display_name:
        return user.agent_profile.display_name
    if hasattr(user, 'client_profile') and user.client_profile.company_name:
        return user.client_profile.company_name
    return user.get_full_name() or user.username or user.email


def build_message_preview(message):
    normalized_text = ' '.join(message.text.split())
    if normalized_text:
        return Truncator(normalized_text).chars(PREVIEW_LENGTH)

    attachments = list(message.attachments.all())
    if not attachments:
        return '[Сообщение без текста]'
    if len(attachments) > 1:
        return f'[Вложения: {len(attachments)}]'

    content_type = attachments[0].content_type.lower()
    if content_type.startswith('image/'):
        return '[Изображение]'
    if content_type.startswith('audio/'):
        return '[Аудиозапись]'
    if content_type.startswith('video/'):
        return '[Видео]'
    return '[Вложение]'


def build_chat_url(message):
    return absolute_platform_url(reverse('chat_room', args=[message.room_id]))


def build_telegram_preview(message):
    normalized_text = ' '.join(message.text.split())
    if not normalized_text:
        return build_message_preview(message)
    if len(normalized_text) > TELEGRAM_PREVIEW_LENGTH:
        return f'{normalized_text[:TELEGRAM_PREVIEW_LENGTH]}...'
    return normalized_text


def enqueue_chat_message_deliveries(message_id):
    """Create the durable notification event after the message transaction commits."""
    from chat.models import Message

    try:
        message = Message.objects.select_related(
            'sender', 'room__performer', 'room__client'
        ).prefetch_related('attachments').get(pk=message_id)
    except Message.DoesNotExist:
        return 0

    recipient = (
        message.room.client
        if message.sender_id == message.room.performer_id
        else message.room.performer
    )
    if recipient.pk == message.sender_id:
        return 0

    notification_type = Notification.NOTIFICATION_TYPE_CHAT_MESSAGE
    preference = NotificationPreference.get_or_create_for(recipient, notification_type)
    channels = get_active_channels(recipient, notification_type)
    preview = build_message_preview(message)
    sender_name = get_user_display_name(message.sender)

    if preference.in_app_enabled or channels:
        Notification.objects.get_or_create(
            user=recipient,
            notification_type=notification_type,
            related_object_id=message.pk,
            related_object_type='chat.message',
            defaults={
                'title': 'Новое сообщение на платформе «Маэстро»',
                'message': f'{sender_name}: {preview}',
                'is_sent': False,
                'email_sent': False,
                'in_app_sent': preference.in_app_enabled,
            },
        )

    created_count = 0
    for channel in channels:
        _, created = NotificationDelivery.objects.get_or_create(
            message=message,
            recipient=recipient,
            channel=channel,
        )
        created_count += int(created)
    return created_count


def _send_email(delivery):
    message = delivery.message
    recipient = delivery.recipient
    sender_name = get_user_display_name(message.sender)
    preview = build_message_preview(message)
    context = {
        'user': recipient,
        'sender_name': sender_name,
        'message_text': preview,
        'message_preview': f'{sender_name}: {preview}',
        'platform_url': build_chat_url(message),
    }
    sent_count = send_mail(
        subject='Проверьте чаты. Вам доставлено новое сообщение.',
        message=render_to_string('notifications/emails/chat_message.txt', context),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient.email],
        html_message=render_to_string('notifications/emails/chat_message.html', context),
        fail_silently=False,
    )
    return sent_count > 0


def _send_telegram(delivery):
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError('Telegram bot token is not configured')

    message = delivery.message
    sender_name = escape(get_user_display_name(message.sender))
    preview = escape(build_telegram_preview(message))
    payload = json.dumps({
        'chat_id': delivery.recipient.telegram_connection.telegram_chat_id,
        'text': f'Новое сообщение от <b>{sender_name}</b>\n\n<i>«{preview}»</i>',
        'parse_mode': 'HTML',
        'reply_markup': {
            'inline_keyboard': [[{
                'text': 'Открыть сообщение',
                'url': build_chat_url(message),
            }]],
        },
    }).encode('utf-8')
    api_request = urllib_request.Request(
        f'https://api.telegram.org/bot{token}/sendMessage',
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    with urllib_request.urlopen(api_request, timeout=settings.TELEGRAM_SEND_TIMEOUT) as response:
        result = json.loads(response.read().decode('utf-8'))
    return bool(result.get('ok'))


def _channel_is_active(delivery):
    return delivery.channel in get_active_channels(
        delivery.recipient,
        Notification.NOTIFICATION_TYPE_CHAT_MESSAGE,
    )


def _claim_next_delivery():
    with transaction.atomic():
        delivery = NotificationDelivery.objects.select_for_update().filter(
            status=NotificationDelivery.STATUS_PENDING,
            next_attempt_at__lte=timezone.now(),
        ).select_related(
            'message__sender',
            'message__room',
            'recipient',
        ).prefetch_related('message__attachments').order_by('created_at', 'id').first()
        if delivery is None:
            return None
        delivery.status = NotificationDelivery.STATUS_PROCESSING
        delivery.attempts += 1
        delivery.save(update_fields=('status', 'attempts', 'updated_at'))
        return delivery


def process_pending_deliveries(limit=100):
    """Process queued deliveries; failures are isolated and retried later."""
    processed = 0
    sent = 0
    for _ in range(limit):
        delivery = _claim_next_delivery()
        if delivery is None:
            break
        processed += 1

        try:
            if not _channel_is_active(delivery):
                delivery.status = NotificationDelivery.STATUS_SKIPPED
                delivery.last_error = 'channel_disabled'
            else:
                delivered = (
                    _send_email(delivery)
                    if delivery.channel == NotificationDelivery.CHANNEL_EMAIL
                    else _send_telegram(delivery)
                )
                if not delivered:
                    raise RuntimeError('External provider rejected the delivery')
                delivery.status = NotificationDelivery.STATUS_SENT
                delivery.sent_at = timezone.now()
                delivery.last_error = ''
                sent += 1
                if delivery.channel == NotificationDelivery.CHANNEL_EMAIL:
                    Notification.objects.filter(
                        user=delivery.recipient,
                        notification_type=Notification.NOTIFICATION_TYPE_CHAT_MESSAGE,
                        related_object_id=delivery.message_id,
                        related_object_type='chat.message',
                    ).update(email_sent=True, is_sent=True)
        except Exception as error:
            delivery.last_error = type(error).__name__[:100]
            if delivery.attempts >= settings.NOTIFICATION_DELIVERY_MAX_ATTEMPTS:
                delivery.status = NotificationDelivery.STATUS_FAILED
            else:
                delivery.status = NotificationDelivery.STATUS_PENDING
                delay = settings.NOTIFICATION_DELIVERY_RETRY_SECONDS * (2 ** (delivery.attempts - 1))
                delivery.next_attempt_at = timezone.now() + timedelta(seconds=delay)
            logger.warning(
                'External notification delivery failed',
                extra={
                    'delivery_id': delivery.pk,
                    'channel': delivery.channel,
                    'attempt': delivery.attempts,
                    'error_type': type(error).__name__,
                },
            )
        delivery.save(update_fields=(
            'status', 'sent_at', 'last_error', 'next_attempt_at', 'updated_at'
        ))
    return {'processed': processed, 'sent': sent}
