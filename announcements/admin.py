from django.contrib import admin

from .models import (
    Announcement,
    AnnouncementResponse,
    AnnouncementResponseAttachment,
    Tag,
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'announcement_type',
        'author',
        'status',
        'is_approved',
        'published_at',
        'application_deadline',
        'response_count',
    )
    list_filter = ('announcement_type', 'status', 'is_approved', 'is_paid', 'is_online', 'is_one_day', 'published_at', 'tags')
    search_fields = ('title', 'description', 'author__username', 'city', 'location')
    autocomplete_fields = ('author', 'tags')
    date_hierarchy = 'published_at'
    readonly_fields = ('created_at', 'updated_at', 'published_at')
    filter_horizontal = ('tags',)
    
    def response_count(self, obj):
        return obj.response_count
    response_count.short_description = 'Откликов'


@admin.register(AnnouncementResponse)
class AnnouncementResponseAdmin(admin.ModelAdmin):
    list_display = ('announcement', 'responder', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('announcement__title', 'responder__username', 'message')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AnnouncementResponseAttachment)
class AnnouncementResponseAttachmentAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'response', 'content_type', 'size', 'created_at')
    search_fields = ('original_name', 'response__responder__username', 'response__announcement__title')
    list_filter = ('content_type', 'created_at')
