from django.contrib import admin
from django.utils.html import format_html
from .models import InventoryCategory, InventoryItem, InventoryTransaction, TransactionType


@admin.register(InventoryCategory)
class InventoryCategoryAdmin(admin.ModelAdmin):
    """Админ-панель для категорий инвентаря."""

    list_display = [
        'id',
        'name',
        'is_active',
        'active_items_count',
        'created_at'
    ]
    list_filter = [
        'is_active',
        'created_at'
    ]
    search_fields = [
        'name',
        'description'
    ]
    ordering = ['name']

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description')
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
    )


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    """Админ-панель для товаров на складе с алертами низкого остатка."""

    list_display = [
        'id',
        'name',
        'category',
        'unit',
        'quantity_display',
        'min_quantity',
        'price_per_unit',
        'stock_status',
        'is_active',
        'updated_at'
    ]
    list_filter = [
        'category',
        'is_active',
        'created_at',
        'updated_at'
    ]
    search_fields = [
        'name',
        'category__name'
    ]
    ordering = ['category', 'name']
    list_editable = ['is_active', 'min_quantity']

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'category', 'unit')
        }),
        ('Остатки и цены', {
            'fields': ('quantity', 'min_quantity', 'price_per_unit')
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def quantity_display(self, obj):
        """Отображение количества с цветовым индикатором."""
        status, _ = obj.get_stock_status()
        if status == 'out':
            color = 'red'
            icon = '❌'
        elif status == 'low':
            color = 'orange'
            icon = '⚠️'
        else:
            color = 'green'
            icon = '✅'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {} {}</span>',
            color,
            icon,
            obj.quantity,
            obj.unit
        )
    quantity_display.short_description = 'Остаток'

    def stock_status(self, obj):
        """Отображение статуса запаса."""
        status, label = obj.get_stock_status()
        if status == 'out':
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 2px 6px; border-radius: 3px;">{}</span>',
                label
            )
        elif status == 'low':
            return format_html(
                '<span style="background-color: #ffc107; color: black; padding: 2px 6px; border-radius: 3px;">{}</span>',
                label
            )
        else:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 2px 6px; border-radius: 3px;">{}</span>',
                label
            )
    stock_status.short_description = 'Статус'


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    """Админ-панель для операций со складом."""

    list_display = [
        'id',
        'item',
        'transaction_type_display',
        'quantity_change',
        'order',
        'employee',
        'created_at'
    ]
    list_filter = [
        'transaction_type',
        'created_at',
        'item__category'
    ]
    search_fields = [
        'item__name',
        'comment',
        'order__order_code',
        'employee__user__full_name'
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Операция', {
            'fields': ('item', 'transaction_type', 'quantity')
        }),
        ('Связи', {
            'fields': ('order', 'employee'),
            'classes': ('collapse',)
        }),
        ('Дополнительно', {
            'fields': ('comment',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at']
    autocomplete_fields = ['item', 'order', 'employee']

    def transaction_type_display(self, obj):
        """Цветовое отображение типа операции."""
        colors = {
            TransactionType.IN: '#28a745',
            TransactionType.OUT: '#dc3545',
            TransactionType.ADJUSTMENT: '#6c757d'
        }
        color = colors.get(obj.transaction_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px;">{}</span>',
            color,
            obj.get_transaction_type_display()
        )
    transaction_type_display.short_description = 'Тип операции'

    def quantity_change(self, obj):
        """Отображение изменения количества со знаком."""
        change = obj.get_quantity_change()
        if obj.transaction_type == TransactionType.IN:
            color = 'green'
        elif obj.transaction_type == TransactionType.OUT:
            color = 'red'
        else:
            color = 'gray'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color,
            change,
            obj.item.unit
        )
    quantity_change.short_description = 'Изменение'
