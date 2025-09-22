from django.contrib import admin
from .models import Client, ClientNote


class ClientNoteInline(admin.TabularInline):  # или StackedInline
    model = ClientNote
    extra = 1  # сколько пустых строк показывать для добавления
    fields = ("text", "created_by", "created_at")
    readonly_fields = ("created_by", "created_at")

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("first_name", "last_name", "phone", "orders_count", "total_spent", "updated_by", "updated_at")
    exclude = ("created_by", "updated_by")  
    readonly_fields = ("orders_count", "first_order_date", "last_order_date", "total_spent","telegram_id")  

    inlines = [ClientNoteInline]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
