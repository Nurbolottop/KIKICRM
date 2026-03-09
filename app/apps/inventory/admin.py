from django.contrib import admin
from .models import Product, Stock, StockMovement, InventoryCheck, InventoryCheckItem, WriteOff


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "unit", "min_quantity", "is_active", "created_at"]
    list_filter = ["category", "is_active", "unit"]
    search_fields = ["name", "description"]
    date_hierarchy = "created_at"


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ["product", "quantity", "last_updated", "is_low_stock"]
    list_filter = ["product__category"]
    search_fields = ["product__name"]
    readonly_fields = ["last_updated"]
    
    def is_low_stock(self, obj):
        return obj.is_low_stock
    is_low_stock.boolean = True
    is_low_stock.short_description = "Низкий остаток"


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["product", "movement_type", "reason", "quantity", "created_by", "created_at"]
    list_filter = ["movement_type", "reason", "created_at"]
    search_fields = ["product__name", "notes"]
    date_hierarchy = "created_at"
    readonly_fields = ["created_at"]


class InventoryCheckItemInline(admin.TabularInline):
    model = InventoryCheckItem
    extra = 0


@admin.register(InventoryCheck)
class InventoryCheckAdmin(admin.ModelAdmin):
    list_display = ["name", "status", "created_by", "created_at", "completed_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["name", "notes"]
    date_hierarchy = "created_at"
    inlines = [InventoryCheckItemInline]
    readonly_fields = ["created_at", "completed_at"]


@admin.register(WriteOff)
class WriteOffAdmin(admin.ModelAdmin):
    list_display = ["product", "quantity", "reason", "created_by", "created_at"]
    list_filter = ["reason", "created_at"]
    search_fields = ["product__name", "notes"]
    date_hierarchy = "created_at"
    readonly_fields = ["created_at"]
