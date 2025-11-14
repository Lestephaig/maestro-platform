from django.contrib import admin
from .models import AgentProfile


@admin.register(AgentProfile)
class AgentProfileAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'agency_name', 'user', 'experience_years', 'trust_level', 'successful_deals', 'total_deals', 'is_verified')
    search_fields = ('display_name', 'agency_name', 'user__username', 'user__email')
    list_filter = ('is_verified',)

