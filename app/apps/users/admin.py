from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.users import models as users_models

@admin.register(users_models.User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username', 'full_name', 'role', 'phone', 'whatsapp_link', 'is_active'
    )
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'full_name', 'phone', 'email')
    ordering = ('-date_joined',)

    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Личная информация', {
            'fields': ('full_name', 'phone', 'whatsapp', 'telegram_id', 'avatar')
        }),
        ('Роль и доступ', {
            'fields': ('role', 'is_active', 'is_superuser', )
        }),
        ('Доп. информация', {
            'fields': ('last_login', 'date_joined')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role', 'full_name', 'phone', 'whatsapp')
        }),
    )

    readonly_fields = ('whatsapp_link', 'last_login', 'date_joined')
