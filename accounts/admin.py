from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    # Поля, которые будут отображаться в списке пользователей
    list_display = ('username', 'email', 'is_verified', 'is_active', 'date_joined')
    # Поля для поиска
    search_fields = ('username', 'email')
    # Фильтры справа
    list_filter = ('is_verified', 'is_active', 'is_staff', 'date_joined')

    # Поля, которые можно редактировать прямо в списке
    list_editable = ('is_verified',)

    # Поля, которые будут отображаться при создании/редактировании пользователя
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )

# Зарегистрируем нашу модель с кастомной админкой
admin.site.register(User, CustomUserAdmin)
