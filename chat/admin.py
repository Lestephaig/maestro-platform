from django.contrib import admin
from .models import ChatRoom, Message, MessageAttachment

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('performer', 'client', 'created_at')
    search_fields = ('performer__username', 'client__username')
    list_filter = ('created_at',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('room', 'sender', 'timestamp', 'is_read')
    list_filter = ('is_read', 'timestamp')
    search_fields = ('text', 'sender__username')


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'message', 'content_type', 'size', 'created_at')
    search_fields = ('original_name', 'message__sender__username')
    list_filter = ('content_type', 'created_at')
