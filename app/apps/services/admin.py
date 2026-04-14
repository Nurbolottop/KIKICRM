from django.contrib import admin
from .models import Service, ExtraService, ServiceCategory


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'color', 'icon', 'ordering']
    ordering = ['ordering', 'name']



@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    """Админ-панель для модели Service."""

    list_display = [
        'id',
        'name',
        'category',
        'room_count',
        'price',
        'senior_cleaner_salary',
        'senior_cleaner_bonus',
        'senior_cleaner_count',
        'cleaner_count',
        'is_active'
    ]
    list_filter = [
        'is_active',
        'category',
    ]
    search_fields = [
        'name'
    ]
    ordering = ['name']

    fieldsets = (
        ('Основная информация', {
            'fields': ('category', 'name', 'description', 'image')
        }),
        ('Детали', {
            'fields': ('room_count', 'price', 'senior_cleaner_salary', 'senior_cleaner_bonus', 'senior_cleaner_count', 'cleaner_count', 'checklist', 'is_active')
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
