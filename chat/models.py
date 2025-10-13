from django.db import models
from accounts.models import User

class ChatRoom(models.Model):
    performer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='performer_chats')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='client_chats')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('performer', 'client')

    def __str__(self):
        return f"Chat: {self.performer} ↔ {self.client}"

class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"From {self.sender} at {self.timestamp}"