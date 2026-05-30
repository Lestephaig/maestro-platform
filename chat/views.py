from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.http import HttpResponseForbidden
from django.db.models import Count, Max, Q
from django.db.models.functions import Coalesce
from .models import ChatRoom, Message
from accounts.models import User
from performers.models import PerformerProfile


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
    return render(request, 'chat/chat_list.html', {'chats': chats})

@login_required
def chat_room(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    # Проверим, есть ли доступ к чату
    if request.user != room.performer and request.user != room.client:
        return HttpResponseForbidden('У вас нет доступа к этому чату.')

    chat_messages = Message.objects.filter(room=room).order_by('timestamp')
    
    # Отмечаем все сообщения от другого пользователя как прочитанные
    Message.objects.filter(
        room=room
    ).exclude(
        sender=request.user
    ).filter(
        is_read=False
    ).update(is_read=True)

    return render(request, 'chat/chat_room.html', {
        'room': room,
        'chat_messages': chat_messages,
    })


@login_required
def send_message(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    # Проверим, есть ли доступ к чату
    if request.user != room.performer and request.user != room.client:
        return redirect('chat_list')

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        if text:
            Message.objects.create(
                room=room,
                sender=request.user,
                text=text
            )

    return redirect('chat_room', room_id=room.id)


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
