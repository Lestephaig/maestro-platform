from django.contrib import admin
from .models import ClientProfile

@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_person', 'user', 'created_at')
    search_fields = ('company_name', 'contact_person')
    list_filter = ('created_at',)
