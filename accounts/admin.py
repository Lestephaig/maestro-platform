from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CookieConsent, LegalAcceptance, User

class CustomUserAdmin(UserAdmin):
    # Поля, которые будут отображаться в списке пользователей
    list_display = ('display_name', 'email', 'role', 'is_verified', 'is_active', 'date_joined')
    # Поля для поиска
    search_fields = ('display_name', 'email', 'username')
    # Фильтры справа
    list_filter = ('role', 'is_verified', 'is_active', 'is_staff', 'date_joined')

    # Поля, которые можно редактировать прямо в списке
    list_editable = ('is_verified',)

    # Поля, которые будут отображаться при создании/редактировании пользователя
    fieldsets = (
        (None, {'fields': ('username', 'email', 'display_name', 'password', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'display_name', 'role', 'password1', 'password2'),
        }),
    )

# Зарегистрируем нашу модель с кастомной админкой
admin.site.register(User, CustomUserAdmin)


@admin.register(LegalAcceptance)
class LegalAcceptanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_title', 'document_version', 'accepted_at', 'ip_address')
    list_filter = ('document_slug', 'document_version', 'accepted_at')
    search_fields = ('user__email', 'user__display_name', 'document_title')
    readonly_fields = ('accepted_at',)


@admin.register(CookieConsent)
class CookieConsentAdmin(admin.ModelAdmin):
    list_display = ('user', 'policy_version', 'accepted_at', 'ip_address')
    list_filter = ('policy_version', 'accepted_at')
    search_fields = ('user__email', 'user__display_name', 'user_agent')
    readonly_fields = ('accepted_at',)
