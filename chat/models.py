import uuid
from pathlib import Path

from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver
from accounts.models import User
from .storage import private_chat_storage


def chat_attachment_upload_to(instance, filename):
    extension = Path(filename).suffix.lower()
    return f'chat/attachments/{instance.message.room_id}/{uuid.uuid4().hex}{extension}'


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
    text = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"From {self.sender} at {self.timestamp}"


class MessageAttachment(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(
        upload_to=chat_attachment_upload_to,
        storage=private_chat_storage,
        max_length=500,
    )
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('id',)

    @property
    def extension(self):
        return Path(self.original_name).suffix.lstrip('.').upper()

    def __str__(self):
        return self.original_name


@receiver(post_delete, sender=MessageAttachment)
def delete_attachment_file(sender, instance, **kwargs):
    if instance.file:
        storage = instance.file.storage
        name = instance.file.name
        transaction.on_commit(lambda: storage.delete(name))
