from django.contrib import admin
from .models import Order, OrderEmployee, OrderStatus, OrderPhoto, RefuseSettings


class OrderEmployeeInline(admin.TabularInline):
    """Inline для назначения сотрудников на заказ."""
    model = OrderEmployee
    extra = 1
    autocomplete_fields = ['employee']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Админ-панель для модели Order."""

    list_display = [
        'id',
        'order_code',
        'client',
        'service',
        'scheduled_date',
        'scheduled_time',
        'status',
        'operator_status',
        'manager_status',
        'senior_cleaner_status',
        'price',
        'created_by'
    ]
    list_filter = [
        'status',
        'operator_status',
        'manager_status',
        'senior_cleaner_status',
        'scheduled_date',
        'service',
        'created_at'
    ]
    list_editable = [
        'operator_status',
        'manager_status',
        'senior_cleaner_status',
    ]
    search_fields = [
        'order_code',
        'client__name',
        'client__phone',
        'address'
    ]
    ordering = ['-scheduled_date', '-scheduled_time']

    readonly_fields = ['order_code', 'created_at', 'updated_at']

    fieldsets = (
        ('Основная информация', {
            'fields': ('order_code', 'client', 'service')
        }),
        ('Детали заказа', {
            'fields': ('address', 'scheduled_date', 'scheduled_time', 'price', 'preliminary_price')
        }),
        ('Статусы', {
            'fields': (
                'status',
                'operator_status',
                'manager_status',
                'senior_cleaner_status',
                'handed_to_manager',
                'handed_to_manager_at',
            ),
            'description': 'Изменяйте статусы вручную только при необходимости.'
        }),
        ('Комментарий', {
            'fields': ('comment',),
            'classes': ('collapse',)
        }),
        ('Назначения', {
            'fields': ('created_by', 'assigned_manager')
        }),
        ('Системные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    autocomplete_fields = ['client', 'service', 'created_by', 'assigned_manager']
    inlines = [OrderEmployeeInline]


@admin.register(OrderEmployee)
class OrderEmployeeAdmin(admin.ModelAdmin):
    """Админ-панель для модели OrderEmployee."""

    list_display = [
        'id',
        'order',
        'employee',
        'role_on_order',
        'is_confirmed',
        'assigned_at',
        'confirmed_at',
        'started_at',
        'finished_at'
    ]
    list_filter = [
        'role_on_order',
        'is_confirmed',
        'assigned_at',
        'started_at',
        'finished_at'
    ]
    search_fields = [
        'order__order_code',
        'employee__user__full_name',
        'employee__user__phone'
    ]
    ordering = ['-assigned_at']

    fieldsets = (
        ('Основная информация', {
            'fields': ('order', 'employee', 'role_on_order')
        }),
        ('Статус', {
            'fields': ('is_confirmed', 'confirmed_at', 'started_at', 'finished_at')
        }),
        ('Заметки', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['assigned_at', 'confirmed_at', 'started_at', 'finished_at']
    autocomplete_fields = ['order', 'employee']


@admin.register(OrderPhoto)
class OrderPhotoAdmin(admin.ModelAdmin):
    """Админ-панель для фото заказов."""

    list_display = [
        'id',
        'order',
        'uploaded_by',
        'photo_type',
        'uploaded_at'
    ]
    list_filter = [
        'photo_type',
        'uploaded_at'
    ]
    search_fields = [
        'order__order_code',
        'uploaded_by__user__full_name',
        'comment'
    ]
    ordering = ['-uploaded_at']
    
    readonly_fields = ['uploaded_at']
    autocomplete_fields = ['order', 'uploaded_by']


@admin.register(RefuseSettings)
class RefuseSettingsAdmin(admin.ModelAdmin):
    """Админ-панель для настроек отказов."""

    list_display = (
        "max_refuses",
        "period_days",
        "is_active",
        "updated_at"
    )

    list_editable = ("is_active",)

    readonly_fields = (
        "created_at",
        "updated_at"
    )
