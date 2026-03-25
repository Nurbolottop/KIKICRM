from django.contrib import admin
from .models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """Админ-панель для расходов."""
    list_display = [
        'id',
        'user',
        'category',
        'amount',
        'expense_date',
        'created_at'
    ]
    list_filter = [
        'category',
        'expense_date'
    ]
    search_fields = [
        'user__full_name',
        'user__phone',
        'description'
    ]
    date_hierarchy = 'expense_date'
