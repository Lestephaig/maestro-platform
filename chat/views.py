from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import ChatRoom,Message

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

    messages = Message.objects.filter(room=room).order_by('timestamp')

    return render(request, 'chat/chat_room.html', {
        'room': room,
        'messages': messages,
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