from django.contrib import admin
from .models import Service, ExtraService


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """Админ-панель для модели Service."""

    list_display = [
        'id',
        'name',
        'room_count',
        'price',
        'senior_cleaner_salary',
        'senior_cleaner_bonus',
        'is_active'
    ]
    list_filter = [
        'is_active'
    ]
    search_fields = [
        'name'
    ]
    ordering = ['name']

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'image')
        }),
        ('Детали', {
            'fields': ('room_count', 'price', 'senior_cleaner_salary', 'senior_cleaner_bonus', 'checklist', 'is_active')
        }),
        ('Системные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']


@admin.register(ExtraService)
class ExtraServiceAdmin(admin.ModelAdmin):
    """Админ-панель для дополнительных услуг."""

    list_display = [
        'id',
        'name',
        'price',
        'is_active'
    ]
    list_filter = [
        'is_active'
    ]
    search_fields = [
        'name'
    ]
    ordering = ['name']

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description')
        }),
        ('Цена и статус', {
            'fields': ('price', 'is_active')
        }),
        ('Системные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']
