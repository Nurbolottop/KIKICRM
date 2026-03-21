from django.contrib import admin
from .models import ChecklistTemplate, ChecklistTemplateTask, OrderTask


class ChecklistTemplateTaskInline(admin.TabularInline):
    """Inline для задач в шаблоне чеклиста."""
    model = ChecklistTemplateTask
    extra = 1
    fields = ['title', 'description', 'order', 'is_active']
    ordering = ['order']


@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    """Админ-панель для шаблонов чеклистов."""
    
    list_display = [
        'id',
        'name',
        'service',
        'is_active',
        'tasks_count',
        'created_at'
    ]
    
    list_filter = ['is_active', 'service', 'created_at']
    
    search_fields = ['name', 'description', 'service__name']
    
    inlines = [ChecklistTemplateTaskInline]
    
    fieldsets = (
        ('Основное', {
            'fields': ('service', 'name', 'description', 'is_active')
        }),
        ('Системное', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def tasks_count(self, obj):
        """Количество задач в шаблоне."""
        return obj.tasks.filter(is_active=True).count()
    tasks_count.short_description = 'Активных задач'


@admin.register(ChecklistTemplateTask)
class ChecklistTemplateTaskAdmin(admin.ModelAdmin):
    """Админ-панель для задач в шаблоне."""
    
    list_display = [
        'id',
        'title',
        'template',
        'order',
        'is_active'
    ]
    
    list_filter = ['is_active', 'template', 'template__service']
    
    search_fields = ['title', 'description', 'template__name']
    
    list_editable = ['order', 'is_active']
    
    ordering = ['template', 'order']


@admin.register(OrderTask)
class OrderTaskAdmin(admin.ModelAdmin):
    """Админ-панель для задач заказа."""
    
    list_display = [
        'id',
        'order',
        'title',
        'assigned_employee',
        'status',
        'started_at',
        'finished_at',
        'duration_display'
    ]
    
    list_filter = [
        'status',
        'created_at',
        'assigned_employee',
        'order__service'
    ]
    
    search_fields = [
        'title',
        'order__order_code',
        'assigned_employee__user__full_name'
    ]
    
    list_editable = ['status', 'assigned_employee']
    
    readonly_fields = [
        'created_at',
        'started_at',
        'finished_at',
        'duration_display'
    ]
    
    fieldsets = (
        ('Заказ', {
            'fields': ('order', 'title', 'description')
        }),
        ('Назначение', {
            'fields': ('assigned_employee', 'order_position')
        }),
        ('Статус', {
            'fields': ('status',)
        }),
        ('Время выполнения', {
            'fields': ('started_at', 'finished_at', 'duration_display'),
            'classes': ('collapse',)
        }),
        ('Примечания', {
            'fields': ('notes', 'finished_by'),
            'classes': ('collapse',)
        }),
        ('Системное', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    def duration_display(self, obj):
        """Отображение длительности."""
        if obj.duration:
            return f'{obj.duration} мин'
        return '—'
    duration_display.short_description = 'Длительность'
