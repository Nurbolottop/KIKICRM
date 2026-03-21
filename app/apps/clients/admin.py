from django.contrib import admin
from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Админ-панель для модели Client."""

    list_display = [
        'id',
        'get_full_name',
        'phone',
        'source',
        'category',
        'created_at'
    ]
    list_filter = [
        'source',
        'category',
        'gender',
        'created_at'
    ]
    search_fields = [
        'first_name',
        'last_name',
        'middle_name',
        'phone',
        'phone_secondary',
        'email'
    ]
    ordering = ['-created_at']

    fieldsets = (
        ('Основная информация', {
            'fields': ('photo', 'last_name', 'first_name', 'middle_name', 'organization')
        }),
        ('Классификация', {
            'fields': ('category', 'source', 'gender')
        }),
        ('Контактные данные', {
            'fields': ('phone', 'phone_secondary', 'whatsapp', 'email', 'birth_date', 'address')
        }),
        ('Дополнительно', {
            'fields': ('notes',)
        }),
        ('Системные', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = 'Имя'
