from django.contrib import admin
from django.utils.html import format_html
from .models import MusicInstrument, PerformerProfile, PerformerAvailability, PerformerPhoto, PerformerVideo, RepertoireItem


@admin.register(MusicInstrument)
class MusicInstrumentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(PerformerProfile)
class PerformerProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'performer_type', 'voice_type', 'instrument', 'birth_date', 'is_verified', 'calendar_mode', 'user', 'created_at', 'photo_preview')
    search_fields = ('full_name', 'voice_type', 'instrument', 'repertoire', 'education', 'achievements')
    list_filter = ('performer_type', 'voice_type', 'instrument', 'birth_date', 'is_verified', 'calendar_mode', 'created_at')
    list_editable = ('is_verified',)
    readonly_fields = ('photo_preview',)
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'full_name', 'country', 'city', 'birth_date', 'photo', 'photo_preview')
        }),
        ('Образование и достижения', {
            'fields': ('education', 'achievements')
        }),
        ('Музыкальная информация', {
            'fields': ('performer_type', 'voice_type', 'instrument', 'repertoire', 'bio')
        }),
        ('Медиа', {
            'fields': ('video_url',)
        }),
        ('Настройки календаря', {
            'fields': ('calendar_mode',)
        }),
        ('Верификация', {
            'fields': ('is_verified',)
        }),
    )
    
    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', obj.photo.url)
        return "-"
    photo_preview.short_description = 'Фото'


@admin.register(PerformerAvailability)
class PerformerAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('performer', 'date', 'status', 'created_at', 'status_color')
    list_filter = ('status', 'date', 'performer')
    search_fields = ('performer__full_name', 'notes')
    date_hierarchy = 'date'
    
    def status_color(self, obj):
        colors = {
            'available': '🟢',
            'busy': '🔴', 
            'maybe': '🟡'
        }
        return colors.get(obj.status, '⚪')
    status_color.short_description = 'Статус'


@admin.register(PerformerPhoto)
class PerformerPhotoAdmin(admin.ModelAdmin):
    list_display = ('performer', 'caption', 'order', 'created_at', 'photo_preview')
    list_filter = ('performer', 'created_at')
    search_fields = ('performer__full_name', 'caption')
    list_editable = ('order',)
    readonly_fields = ('photo_preview',)
    
    def photo_preview(self, obj):
        if obj.photo:
            return format_html('<img src="{}" width="50" height="50" />', obj.photo.url)
        return "-"
    photo_preview.short_description = 'Превью'


@admin.register(PerformerVideo)
class PerformerVideoAdmin(admin.ModelAdmin):
    list_display = ('performer', 'title', 'order', 'created_at', 'video_link')
    list_filter = ('performer', 'created_at')
    search_fields = ('performer__full_name', 'title', 'description')
    list_editable = ('order',)
    
    def video_link(self, obj):
        if obj.video_url:
            return format_html('<a href="{}" target="_blank">📺 Смотреть</a>', obj.video_url)
        return "-"
    video_link.short_description = 'Видео'


@admin.register(RepertoireItem)
class RepertoireItemAdmin(admin.ModelAdmin):
    list_display = ('performer', 'composer', 'work_title', 'category', 'epoch', 'role_or_part', 'is_featured', 'order', 'created_at', 'featured_badge')
    list_filter = ('category', 'epoch', 'is_featured', 'performer')
    search_fields = ('composer', 'work_title', 'role_or_part', 'performer__full_name')
    list_editable = ('order', 'is_featured')
    fieldsets = (
        ('Основная информация', {
            'fields': ('performer', 'composer', 'work_title')
        }),
        ('Классификация', {
            'fields': ('category', 'epoch', 'role_or_part')
        }),
        ('Дополнительно', {
            'fields': ('year_performed', 'notes', 'video_link')
        }),
        ('Настройки отображения', {
            'fields': ('is_featured', 'order')
        }),
    )
    
    def featured_badge(self, obj):
        if obj.is_featured:
            return format_html('<span style="color: green; font-weight: bold;">★ Избранное</span>')
        return ""
    featured_badge.short_description = 'Статус'
