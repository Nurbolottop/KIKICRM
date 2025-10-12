from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from apps.users import models as users_models


@admin.register(users_models.User)
class UserAdmin(BaseUserAdmin):
    # --- Список пользователей (таблица) ---
    list_display = (
        'username', 'full_name', 'role', 'status',
        'phone', 'whatsapp_link', 'telegram_id',
        'hire_date', 'payment_type',
        'avatar_preview', 'is_active'
    )
    list_filter = ('role', 'status', 'is_active', 'payment_type')
    search_fields = ('username', 'full_name', 'phone', 'email')
    ordering = ('-date_joined',)

    # --- Детальная карточка пользователя ---
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Личная информация', {
            'fields': ('full_name', 'phone', 'whatsapp', 'telegram_id', 'email')
        }),
        ('Фото и документы', {
            'fields': ('avatar', 'avatar_preview', 'passport_front', 'passport_back')
        }),
        ('Рабочая информация', {
            'fields': ('role', 'status', 'hire_date')
        }),
        ('Финансы', {
            'fields': ('payment_type',)
        }),
        ('Доступ и права', {
            'fields': ('is_active', 'is_superuser')
        }),
        ('Системная информация', {
            'fields': ('last_login', 'date_joined')
        }),
    )

    # --- Форма добавления нового пользователя ---
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'password1', 'password2',
                'role', 'status', 'full_name',
                'phone', 'whatsapp', 'telegram_id',
                'hire_date', 'payment_type', 'avatar'
            ),
        }),
    )

    readonly_fields = ('whatsapp_link', 'last_login', 'date_joined', 'avatar_preview')

    # --- Превью аватара ---
    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width:50px; height:50px; border-radius:50%; object-fit:cover;" />',
                obj.avatar.url
            )
        return "—"
    avatar_preview.short_description = "Аватар"
