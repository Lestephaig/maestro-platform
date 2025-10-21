from django.contrib import admin
from .models import PerformerProfile

@admin.register(PerformerProfile)
class PerformerProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'birth_year', 'voice_type', 'user', 'created_at')
    search_fields = ('full_name', 'voice_type', 'repertoire', 'education', 'achievements')
    list_filter = ('voice_type', 'birth_year', 'created_at')
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'full_name', 'birth_year', 'photo')
        }),
        ('Образование и достижения', {
            'fields': ('education', 'achievements')
        }),
        ('Музыкальная информация', {
            'fields': ('voice_type', 'repertoire', 'bio')
        }),
        ('Медиа', {
            'fields': ('video_url',)
        }),
    )