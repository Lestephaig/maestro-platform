from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_sent', 'sent_at')
    list_filter = ('notification_type', 'is_sent', 'sent_at')
    search_fields = ('user__username', 'user__email', 'title', 'message')
    readonly_fields = ('sent_at',)
    date_hierarchy = 'sent_at'

