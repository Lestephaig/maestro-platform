from django.contrib import admin
from .models import PerformerProfile

@admin.register(PerformerProfile)
class PerformerProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'voice_type', 'user', 'created_at')
    search_fields = ('full_name', 'voice_type', 'repertoire')
    list_filter = ('voice_type', 'created_at')