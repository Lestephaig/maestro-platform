from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from .models import Notification


def send_notification_email(user, notification_type, title, message, context=None, related_object_id=None, related_object_type=None):
    """Отправляет email уведомление пользователю"""
    
    # Проверяем, не отправляли ли мы уже такое уведомление
    if related_object_id and related_object_type:
        recent_notification = Notification.objects.filter(
            user=user,
            notification_type=notification_type,
            related_object_id=related_object_id,
            related_object_type=related_object_type,
            is_sent=True,
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
    
    # Отправляем email
    try:
        send_mail(
            subject=subject,
            message=message_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        # Сохраняем уведомление в БД
        Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            related_object_id=related_object_id,
            related_object_type=related_object_type,
            is_sent=True,
        )
        return True
    except Exception as e:
        # Сохраняем неудачную попытку
        Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            related_object_id=related_object_id,
            related_object_type=related_object_type,
            is_sent=False,
        )
        return False


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
            is_sent=True
        ).exists()
        
        if not notification_exists:
            # Отправляем уведомление
            sender_name = message.sender.username
            if hasattr(message.sender, 'performer_profile'):
                sender_name = message.sender.performer_profile.full_name
            elif hasattr(message.sender, 'agent_profile'):
                sender_name = message.sender.agent_profile.display_name
            elif hasattr(message.sender, 'client_profile'):
                sender_name = message.sender.client_profile.company_name
            
            send_notification_email(
                user=recipient,
                notification_type=Notification.NOTIFICATION_TYPE_CHAT_MESSAGE,
                title='Новое сообщение в чате',
                message=f'У вас новое сообщение от {sender_name}',
                context={
                    'sender_name': sender_name,
                    'message_text': message.text[:100],  # Первые 100 символов
                    'chat_url': f'{getattr(settings, "SITE_URL", "http://127.0.0.1:8000")}/chat/{message.room.id}/',
                },
                related_object_id=message.id,
                related_object_type='chat.message'
            )

