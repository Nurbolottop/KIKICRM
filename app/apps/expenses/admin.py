from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """Админ-панель для расходов."""
    list_display = [
        'id',
        'employee',
        'category',
        'amount',
        'expense_date',
        'is_general',
        'created_at'
    ]
    list_filter = [
        'category',
        'is_general',
        'expense_date'
    ]
    search_fields = [
        'employee__user__full_name',
        'employee__user__phone',
        'description'
    ]
    date_hierarchy = 'expense_date'
