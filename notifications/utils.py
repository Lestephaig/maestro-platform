import logging

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from .models import Notification, NotificationPreference

logger = logging.getLogger(__name__)


def _absolute_platform_url(path):
    site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')
    return f'{site_url}{path}'


def get_user_display_name(user):
    """Возвращает понятное имя пользователя для писем и уведомлений."""
    if getattr(user, 'display_name', ''):
        return user.display_name
    if hasattr(user, 'performer_profile') and getattr(user.performer_profile, 'full_name', ''):
        return user.performer_profile.full_name
    if hasattr(user, 'agent_profile') and getattr(user.agent_profile, 'display_name', ''):
        return user.agent_profile.display_name
    if hasattr(user, 'client_profile') and getattr(user.client_profile, 'company_name', ''):
        return user.client_profile.company_name
    return user.email or user.username


def send_new_message_email(user, sender, message_text, platform_url=None, related_object_id=None, related_object_type='chat.message'):
    """Отправляет письмо о новом сообщении в едином шаблоне платформы."""
    if not user.email:
        return False

    notification_type = Notification.NOTIFICATION_TYPE_CHAT_MESSAGE
    preference = NotificationPreference.get_or_create_for(user, notification_type)
    if not preference.in_app_enabled and not preference.email_enabled:
        return False

    sender_name = get_user_display_name(sender)
    message_preview = f'{sender_name}: {message_text}'
    if platform_url and platform_url.startswith('/'):
        platform_url = _absolute_platform_url(platform_url)
    platform_url = platform_url or _absolute_platform_url('/chat/')

    if related_object_id and related_object_type:
        recent_notification = Notification.objects.filter(
            user=user,
            notification_type=notification_type,
            related_object_id=related_object_id,
            related_object_type=related_object_type,
        ).exists()
        if recent_notification:
            return False

    context = {
        'user': user,
        'sender_name': sender_name,
        'message_text': message_text,
        'message_preview': message_preview,
        'platform_url': platform_url,
    }
    subject = 'Проверьте чаты. Вам доставлено новое сообщение.'
    text_message = render_to_string('notifications/emails/chat_message.txt', context)
    html_message = render_to_string('notifications/emails/chat_message.html', context)

    should_send_email = preference.email_enabled and getattr(user, 'is_email_verified', False)
    email_sent = False
    if should_send_email:
        try:
            sent_count = send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            email_sent = sent_count > 0
        except Exception:
            logger.exception('Failed to send new message email to user %s', user.pk)
            if settings.DEBUG:
                raise

    if preference.in_app_enabled or should_send_email:
        Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title='Новое сообщение на платформе «Маэстро»',
            message=message_preview,
            related_object_id=related_object_id,
            related_object_type=related_object_type,
            is_sent=email_sent,
            email_sent=email_sent,
            in_app_sent=preference.in_app_enabled,
        )

    return email_sent


def send_notification_email(user, notification_type, title, message, context=None, related_object_id=None, related_object_type=None):
    """Создает системное уведомление и, при настройке, отправляет email."""
    preference = NotificationPreference.get_or_create_for(user, notification_type)
    if not preference.in_app_enabled and not preference.email_enabled:
        return False
    
    # Проверяем, не отправляли ли мы уже такое уведомление
    if related_object_id and related_object_type:
        recent_notification = Notification.objects.filter(
            user=user,
            notification_type=notification_type,
            related_object_id=related_object_id,
            related_object_type=related_object_type,
            title=title,
            message=message,
            sent_at__gte=timezone.now() - timedelta(hours=1)  # Не отправляем дубликаты в течение часа
        ).exists()
        
        if recent_notification:
            return False
    
    # Создаем контекст для шаблона
    template_context = {
        'user': user,
        'title': title,
        'message': message,
        'site_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000'),
    }
    if context:
        template_context.update(context)
    
    # Тема письма
    subject = f'Maestro Platform - {title}'
    
    # Текст письма
    text_template = f'notifications/emails/{notification_type}.txt'
    html_template = f'notifications/emails/{notification_type}.html'
    
    try:
        message_text = render_to_string(text_template, template_context)
        html_message = render_to_string(html_template, template_context)
    except:
        # Если шаблона нет, используем базовый
        message_text = message
        html_message = None
    
    should_send_email = preference.email_enabled and getattr(user, 'is_email_verified', False)
    in_app_sent = preference.in_app_enabled
    email_sent = False
    if should_send_email:
        try:
            send_mail(
                subject=subject,
                message=message_text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            email_sent = True
        except Exception:
            email_sent = False

    # Сохраняем уведомление в БД с независимыми статусами каналов
    if in_app_sent or should_send_email:
        Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            related_object_id=related_object_id,
            related_object_type=related_object_type,
            is_sent=email_sent,
            email_sent=email_sent,
            in_app_sent=in_app_sent,
        )
    return email_sent


def check_unread_chat_messages():
    """Проверяет непрочитанные сообщения в чате и отправляет уведомления через 5 минут"""
    from chat.models import Message
    from datetime import timedelta
    
    # Находим сообщения, которые не прочитаны более 5 минут
    five_minutes_ago = timezone.now() - timedelta(minutes=5)
    
    unread_messages = Message.objects.filter(
        is_read=False,
        timestamp__lte=five_minutes_ago
    ).select_related('room', 'sender', 'room__performer', 'room__client')
    
    for message in unread_messages:
        # Определяем получателя (не отправителя)
        recipient = message.room.client if message.sender == message.room.performer else message.room.performer
        
        # Проверяем, не отправляли ли уже уведомление для этого сообщения
        notification_exists = Notification.objects.filter(
            user=recipient,
            notification_type=Notification.NOTIFICATION_TYPE_CHAT_MESSAGE,
            related_object_id=message.id,
            related_object_type='chat.message',
            email_sent=True
        ).exists()
        
        if not notification_exists:
            send_new_message_email(
                user=recipient,
                sender=message.sender,
                message_text=message.text,
                platform_url=f'/chat/{message.room.id}/',
                related_object_id=message.id,
                related_object_type='chat.message'
            )


def notify_performers_about_announcement_by_tags(announcement):
    """Уведомляет исполнителей о новом объявлении по совпадающим тегам."""
    from performers.models import PerformerProfile

    if announcement.status != announcement.STATUS_PUBLISHED or not announcement.is_approved:
        return 0

    tag_names = list(announcement.tags.values_list('name', flat=True))
    normalized_tags = {name.strip().lower() for name in tag_names if name and name.strip()}
    if not normalized_tags:
        return 0

    performers = PerformerProfile.objects.select_related('user').exclude(user=announcement.author)
    notified_users = set()
    sent_count = 0

    for performer in performers:
        user = performer.user
        if user.id in notified_users:
            continue
        candidate_values = {
            (performer.voice_type or '').strip().lower(),
            (performer.instrument or '').strip().lower(),
        }
        candidate_values.discard('')
        matched_tags = sorted(
            name for name in tag_names if name and name.strip().lower() in candidate_values
        )
        if not matched_tags:
            continue

        sent = send_notification_email(
            user=user,
            notification_type=Notification.NOTIFICATION_TYPE_ANNOUNCEMENT_TAG_MATCH,
            title=f'Новые подходящие объявления: {announcement.title}',
            message=(
                f'Появилось новое подходящее объявление по вашим тегам: '
                f'{", ".join(matched_tags)}.'
            ),
            context={
                'announcement_title': announcement.title,
                'announcement_description': announcement.description[:220],
                'matched_tags': matched_tags,
                'announcement_url': f'/announcements/{announcement.id}/',
            },
            related_object_id=announcement.id,
            related_object_type='announcements.announcement',
        )
        notified_users.add(user.id)
        if sent:
            sent_count += 1

    return sent_count

