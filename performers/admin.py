from django.contrib import admin
from .models import PerformerProfile, PerformerAvailability, PerformerPhoto, PerformerVideo, RepertoireItem

@admin.register(PerformerProfile)
class PerformerProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'performer_type', 'voice_type', 'instrument', 'birth_date', 'is_verified', 'calendar_mode', 'user', 'created_at')
    search_fields = ('full_name', 'voice_type', 'instrument', 'repertoire', 'education', 'achievements')
    list_filter = ('performer_type', 'voice_type', 'instrument', 'birth_date', 'is_verified', 'calendar_mode', 'created_at')
    list_editable = ('is_verified',)
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'full_name', 'birth_date', 'photo')
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


@admin.register(PerformerAvailability)
class PerformerAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('performer', 'date', 'status', 'created_at')
    list_filter = ('status', 'date', 'performer')
    search_fields = ('performer__full_name', 'notes')
    date_hierarchy = 'date'


@admin.register(PerformerPhoto)
class PerformerPhotoAdmin(admin.ModelAdmin):
    list_display = ('performer', 'caption', 'order', 'created_at')
    list_filter = ('performer', 'created_at')
    search_fields = ('performer__full_name', 'caption')
    list_editable = ('order',)


@admin.register(PerformerVideo)
class PerformerVideoAdmin(admin.ModelAdmin):
    list_display = ('performer', 'title', 'order', 'created_at')
    list_filter = ('performer', 'created_at')
    search_fields = ('performer__full_name', 'title', 'description')
    list_editable = ('order',)


@admin.register(RepertoireItem)
class RepertoireItemAdmin(admin.ModelAdmin):
    list_display = ('performer', 'composer', 'work_title', 'category', 'epoch', 'role_or_part', 'is_featured', 'order', 'created_at')
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