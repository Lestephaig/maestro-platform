import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import ChatRoom, Message
from accounts.models import User

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        # Проверим, авторизован ли пользователь
        user = self.scope['user']
        if not user.is_authenticated:
            await self.close()
            return

        # Проверим, существует ли чат и есть ли доступ (через sync_to_async)
        try:
            room = await sync_to_async(ChatRoom.objects.select_related('performer', 'client').get)(id=self.room_id)
            # Теперь performer и client уже загружены, можно использовать безопасно
            if user != room.performer and user != room.client:
                await self.close()
                return
        except ChatRoom.DoesNotExist:
            await self.close()
            return

        # Подключаемся к группе
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Отключаемся от группы
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        user_id = self.scope['user'].id

        # Сохраним сообщение в БД
        await self.save_message(self.room_id, user_id, message)

        # Рассылка всем в группе
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_id': user_id,
            }
        )

    async def chat_message(self, event):
        message = event['message']
        sender_id = event['sender_id']

        # Отправим сообщение клиенту
        await self.send(text_data=json.dumps({
            'message': message,
            'sender_id': sender_id,
        }))

    @sync_to_async
    def save_message(self, room_id, user_id, text):
        room = ChatRoom.objects.get(id=room_id)
        user = User.objects.get(id=user_id)
        message = Message.objects.create(room=room, sender=user, text=text)
        
        # Отмечаем все предыдущие сообщения от другого пользователя как прочитанные
        # (так как пользователь сейчас онлайн и видит чат)
        Message.objects.filter(
            room=room
        ).exclude(
            sender=user
        ).filter(
            is_read=False
        ).update(is_read=True)
        
        return message