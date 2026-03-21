from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserRole


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Админ-панель для кастомной модели User с phone-аутентификацией."""

    list_display = [
        'id',
        'full_name',
        'phone',
        'role',
        'is_staff',
        'is_active',
        'date_joined'
    ]
    list_filter = [
        'role',
        'is_staff',
        'is_active',
        'is_superuser',
        'date_joined'
    ]
    search_fields = [
        'full_name',
        'phone'
    ]
    ordering = ['id']

    fieldsets = (
        (None, {
            'fields': ('phone', 'password')
        }),
        ('Персональная информация', {
            'fields': ('full_name', 'role')
        }),
        ('Статусы', {
            'fields': ('is_active', 'is_staff', 'is_superuser')
        }),
        ('Важные даты', {
            'fields': ('date_joined',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'full_name', 'role', 'password1', 'password2'),
        }),
    )

    # Убираем группы, так как используем кастомные роли
    filter_horizontal = ()
