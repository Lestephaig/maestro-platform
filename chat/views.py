from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.http import HttpResponseForbidden
from .models import ChatRoom, Message
from performers.models import PerformerProfile

@login_required
def chat_list(request):
    # Показываем чаты, где пользователь — исполнитель или заказчик
    chats = ChatRoom.objects.filter(
        performer=request.user
    ).union(
        ChatRoom.objects.filter(client=request.user)
    )
    return render(request, 'chat/chat_list.html', {'chats': chats})

@login_required
def chat_room(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    # Проверим, есть ли доступ к чату
    if request.user != room.performer and request.user != room.client:
        return render(request, 'chat/chat_list.html', {'chats': []})  # или 403

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
    
    # Проверяем, верифицирован ли текущий пользователь
    if not request.user.is_verified:
        django_messages.error(request, 'Чат доступен только верифицированным пользователям.')
        return redirect('performer_detail', performer_id=performer_id)
    
    # Получаем профиль исполнителя
    performer_profile = get_object_or_404(PerformerProfile, id=performer_id)
    performer_user = performer_profile.user
    
    # Проверяем, что пользователь не пытается создать чат с самим собой
    if request.user == performer_user:
        django_messages.error(request, 'Вы не можете создать чат с самим собой.')
        return redirect('performer_detail', performer_id=performer_id)
    
    # Ищем существующий чат или создаем новый
    chat_room, created = ChatRoom.objects.get_or_create(
        performer=performer_user,
        client=request.user
    )
    
    if created:
        django_messages.success(request, f'Чат с {performer_profile.full_name} создан!')
    
    return redirect('chat_room', room_id=chat_room.id)