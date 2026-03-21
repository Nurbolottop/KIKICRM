from django.contrib import admin
from django.utils import timezone
from .models import Employee, EmployeeStatus
from .models import EmployeeEarning


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    """Админ-панель для модели Employee."""

    list_display = [
        'id',
        'user',
        'employee_code',
        'status',
        'hire_date',
        'get_user_full_name',
        'get_user_phone'
    ]
    list_filter = [
        'status',
        'hire_date',
        'created_at'
    ]
    search_fields = [
        'user__full_name',
        'user__phone',
        'employee_code',
        'phone_secondary'
    ]
    ordering = ['-created_at']

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'employee_code', 'status')
        }),
        ('Контакты', {
            'fields': ('phone_secondary', 'avatar')
        }),
        ('Даты', {
            'fields': ('hire_date', 'fire_date')
        }),
        ('Дополнительно', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Системные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def get_user_full_name(self, obj):
        """Возвращает полное имя пользователя для отображения в списке."""
        return obj.get_user_full_name() if obj.user else '-'
    get_user_full_name.short_description = 'Имя'

    def get_user_phone(self, obj):
        """Возвращает телефон пользователя для отображения в списке."""
        return obj.get_user_phone() if obj.user else '-'
    get_user_phone.short_description = 'Телефон'


@admin.register(EmployeeEarning)
class EmployeeEarningAdmin(admin.ModelAdmin):
    """Админ-панель для начислений сотрудникам."""

    list_display = ['id', 'employee', 'order', 'role_on_order', 'amount', 'earned_at', 'is_paid', 'paid_at']
    list_filter = ['is_paid', 'earned_at', 'paid_at', 'role_on_order']
    search_fields = ['employee__user__full_name', 'employee__user__phone', 'order__order_code']
    date_hierarchy = 'earned_at'
    actions = ['mark_as_paid']

    @admin.action(description='Отметить как оплачено (обнулить к выплате)')
    def mark_as_paid(self, request, queryset):
        queryset.filter(is_paid=False).update(is_paid=True, paid_at=timezone.now())
