from django.contrib import admin
from .models import Order, Task


class TaskInline(admin.TabularInline):
    model = Task
    extra = 1
    fields = ("description", "cleaner", "status", "photo_before", "photo_after", "comment")
    show_change_link = True


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("code", "client", "service", "channel", "source", "status_operator", "status_manager", "operator", "manager_comment", "created_at")
    list_filter = ("status_operator", "status_manager", "priority", "channel", "source", "created_at")
    search_fields = ("code", "client__full_name", "service__title", "channel", "source", "address", "notes")
    ordering = ("-created_at",)

    fieldsets = (
        ("Основная информация", {"fields": ("code", "client", "category", "status_operator", "status_manager")}),
        ("Детали заказа", {"fields": ("service", "address", "date_time", "estimated_cost", "estimated_area", "final_cost", "final_area", "notes")}),
        ("Маркетинг", {"fields": ("channel", "source")}),
        ("Сотрудники", {"fields": ("operator", "senior_cleaner", "cleaners", "deadline", "manager_comment")}),
        ("Служебное", {"fields": ("created_at", "updated_at")}),
    )

    readonly_fields = ("code", "created_at", "updated_at")
    inlines = [TaskInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("description", "order", "cleaner", "status")
    list_filter = ("status", "cleaner")
    search_fields = ("description", "order__code", "cleaner__full_name")
    ordering = ("status", "id")
