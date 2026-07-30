import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponseForbidden, JsonResponse
from django.db.models import Count, Max, Q
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.views.decorators.http import require_POST

from .attachments import (
    ATTACHMENT_ACCEPT,
    normalized_content_type,
    safe_attachment_name,
    validate_attachments,
)
from .models import ChatRoom, Message, MessageAttachment
from accounts.models import User
from performers.models import PerformerProfile


logger = logging.getLogger(__name__)


def _serialize_attachment(attachment):
    return {
        'id': attachment.id,
        'name': attachment.original_name,
        'extension': attachment.extension,
        'size': attachment.size,
        'content_type': attachment.content_type,
        'open_url': reverse('open_chat_attachment', args=[attachment.id]),
        'download_url': reverse('download_chat_attachment', args=[attachment.id]),
    }


def _serialize_message(message):
    return {
        'id': message.id,
        'message': message.text,
        'sender_id': message.sender_id,
        'timestamp': message.timestamp.isoformat(),
        'attachments': [
            _serialize_attachment(attachment)
            for attachment in message.attachments.all()
        ],
    }


def _broadcast_message(message):
    try:
        async_to_sync(get_channel_layer().group_send)(
            f'chat_{message.room_id}',
            {
                'type': 'chat_message',
                **_serialize_message(message),
            },
        )
    except Exception:
        # The POST response remains usable when Redis/Channels is unavailable.
        logger.warning('Could not broadcast chat message %s', message.id, exc_info=True)


def _get_or_create_chat_room(user_a, user_b):
    """Возвращает общий чат двух пользователей (в любом порядке) или создает его."""
    existing_room = ChatRoom.objects.filter(
        Q(performer=user_a, client=user_b) | Q(performer=user_b, client=user_a)
    ).order_by('created_at', 'id').first()
    if existing_room:
        return existing_room, False

    # Фиксируем порядок пары, чтобы не создавать дубли в обратном направлении
    performer_user, client_user = (user_a, user_b) if user_a.id < user_b.id else (user_b, user_a)
    room, created = ChatRoom.objects.get_or_create(
        performer=performer_user,
        client=client_user,
    )
    return room, created


def _get_user_public_name(user):
    """Возвращает отображаемое имя собеседника с безопасными fallback-ами."""
    if hasattr(user, 'performer_profile') and getattr(user.performer_profile, 'full_name', ''):
        return user.performer_profile.full_name
    if hasattr(user, 'agent_profile') and getattr(user.agent_profile, 'display_name', ''):
        return user.agent_profile.display_name
    if hasattr(user, 'client_profile') and getattr(user.client_profile, 'company_name', ''):
        return user.client_profile.company_name
    if getattr(user, 'display_name', ''):
        return user.display_name
    if getattr(user, 'username', ''):
        return user.username
    if getattr(user, 'email', ''):
        return user.email
    return f'Пользователь #{user.id}'


def _get_user_public_url(user):
    if hasattr(user, 'performer_profile'):
        return reverse('performers:performer_detail', args=[user.performer_profile.id])
    if hasattr(user, 'agent_profile'):
        return reverse('agent_public_profile', args=[user.id])
    if hasattr(user, 'client_profile'):
        return reverse('client_public_profile', args=[user.id])
    return None


@login_required
def chat_list(request):
    # Показываем чаты пользователя, сначала самые активные.
    chats = ChatRoom.objects.filter(
        Q(performer=request.user) | Q(client=request.user)
    ).select_related(
        'performer',
        'client',
    ).annotate(
        last_message_at=Max('messages__timestamp'),
        last_activity_at=Coalesce(Max('messages__timestamp'), 'created_at'),
        unread_count=Count(
            'messages',
            filter=Q(messages__is_read=False) & ~Q(messages__sender=request.user),
        ),
    ).order_by('-last_activity_at', '-created_at')
    chat_items = []
    for chat in chats:
        target = chat.client if request.user == chat.performer else chat.performer
        chat.target_user = target
        chat.target_display_name = _get_user_public_name(target)
        chat.target_profile_url = _get_user_public_url(target)
        chat_items.append(chat)

    return render(request, 'chat/chat_list.html', {'chats': chat_items})

@login_required
def chat_room(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    # Проверим, есть ли доступ к чату
    if request.user != room.performer and request.user != room.client:
        return HttpResponseForbidden('У вас нет доступа к этому чату.')

    chat_messages = Message.objects.filter(room=room).prefetch_related(
        'attachments'
    ).order_by('timestamp')
    
    # Отмечаем все сообщения от другого пользователя как прочитанные
    Message.objects.filter(
        room=room
    ).exclude(
        sender=request.user
    ).filter(
        is_read=False
    ).update(is_read=True)

    target = room.client if request.user == room.performer else room.performer

    return render(request, 'chat/chat_room.html', {
        'room': room,
        'chat_messages': chat_messages,
        'target_display_name': _get_user_public_name(target),
        'target_profile_url': _get_user_public_url(target),
        'attachment_accept': ATTACHMENT_ACCEPT,
        'attachment_max_size_mb': settings.CHAT_ATTACHMENT_MAX_SIZE_MB,
        'attachment_max_count': settings.CHAT_ATTACHMENT_MAX_COUNT,
    })


@login_required
@require_POST
def send_message(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    if request.user != room.performer and request.user != room.client:
        return HttpResponseForbidden('У вас нет доступа к этому чату.')

    text = request.POST.get('text', '').strip()
    files = request.FILES.getlist('attachments')
    if not text and not files:
        return JsonResponse({'error': 'Введите сообщение или прикрепите файл.'}, status=400)

    try:
        validate_attachments(files)
    except ValidationError as exc:
        return JsonResponse({'error': exc.messages[0]}, status=400)

    with transaction.atomic():
        message = Message.objects.create(
            room=room,
            sender=request.user,
            text=text,
        )
        for upload in files:
            MessageAttachment.objects.create(
                message=message,
                file=upload,
                original_name=safe_attachment_name(upload.name),
                content_type=normalized_content_type(upload),
                size=upload.size,
            )

    message = Message.objects.prefetch_related('attachments').get(pk=message.pk)
    payload = _serialize_message(message)
    _broadcast_message(message)
    return JsonResponse(payload, status=201)


def _attachment_response(request, attachment_id, download):
    attachment = get_object_or_404(
        MessageAttachment.objects.select_related(
            'message__room__performer',
            'message__room__client',
        ),
        id=attachment_id,
    )
    room = attachment.message.room
    if request.user != room.performer and request.user != room.client:
        raise Http404

    try:
        response = FileResponse(
            attachment.file.open('rb'),
            as_attachment=download,
            filename=attachment.original_name,
            content_type=attachment.content_type,
        )
    except FileNotFoundError:
        raise Http404('Файл не найден.')
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; sandbox"
    return response


@login_required
def open_attachment(request, attachment_id):
    return _attachment_response(request, attachment_id, download=False)


@login_required
def download_attachment(request, attachment_id):
    return _attachment_response(request, attachment_id, download=True)


@login_required
def start_chat_with_performer(request, performer_id):
    """Создает чат с исполнителем или открывает уже существующий"""
    if not request.user.is_email_verified:
        django_messages.warning(request, 'Подтвердите email, чтобы создавать чаты.')
        return redirect(request.META.get('HTTP_REFERER', 'profile'))

    # Получаем профиль исполнителя
    performer_profile = get_object_or_404(PerformerProfile, id=performer_id)
    performer_user = performer_profile.user
    
    # Проверяем, что пользователь не пытается создать чат с самим собой
    if request.user == performer_user:
        django_messages.error(request, 'Вы не можете создать чат с самим собой.')
        return redirect('performers:performer_detail', performer_id=performer_id)
    
    # Ищем существующий чат в любом порядке или создаем новый
    chat_room, created = _get_or_create_chat_room(request.user, performer_user)
    
    if created:
        django_messages.success(request, f'Чат с {performer_profile.full_name} создан!')
    
    return redirect('chat_room', room_id=chat_room.id)


@login_required
def start_chat_with_user(request, user_id):
    """Создает чат с любым пользователем или открывает уже существующий"""
    if not request.user.is_email_verified:
        django_messages.warning(request, 'Подтвердите email, чтобы создавать чаты.')
        return redirect(request.META.get('HTTP_REFERER', 'profile'))

    target_user = get_object_or_404(User, id=user_id)

    # Проверяем, что пользователь не пытается создать чат с самим собой
    if request.user == target_user:
        django_messages.error(request, 'Вы не можете создать чат с самим собой.')
        return redirect(request.META.get('HTTP_REFERER', 'chat_list'))

    chat_room, created = _get_or_create_chat_room(request.user, target_user)

    if created:
        django_messages.success(request, f'Чат с {target_user.display_name or target_user.email} создан!')

    return redirect('chat_room', room_id=chat_room.id)
