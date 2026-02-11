from django.contrib import admin
from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'is_read', 'in_app_sent', 'email_sent', 'sent_at')
    list_filter = ('notification_type', 'is_read', 'in_app_sent', 'email_sent', 'sent_at')
    search_fields = ('user__username', 'user__email', 'title', 'message')
    readonly_fields = ('sent_at', 'read_at')
    date_hierarchy = 'sent_at'


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'in_app_enabled', 'email_enabled', 'updated_at')
    list_filter = ('notification_type', 'in_app_enabled', 'email_enabled', 'updated_at')
    search_fields = ('user__username', 'user__email')

