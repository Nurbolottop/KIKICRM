from django.contrib import admin
from .models import Order, Task


class TaskInline(admin.TabularInline):
    model = Task
    extra = 1
    fields = ("description", "status", "photo_before", "photo_after", "comment")
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
        ("Сотрудники", {"fields": ("operator", "deadline", "manager_comment")}),
        ("Служебное", {"fields": ("created_at", "updated_at")}),
    )

    readonly_fields = ("code", "created_at", "updated_at")
    inlines = [TaskInline]

    actions = [
        "revert_to_in_progress",
    ]

    def revert_to_in_progress(self, request, queryset):
        """Отменить отправку на проверку: вернуть заказ в работу.
        - Меняет статус менеджера на IN_PROGRESS
        - Очищает отметку о завершении работы (work_finished_at)
        - Поле статуса старшего клинера удалено
        """
        updated = 0
        for order in queryset:
            if order.status_manager == Order.ManagerStatus.PENDING_REVIEW:
                order.status_manager = Order.ManagerStatus.IN_PROGRESS
                # Вернуть процесс в работу
                order.work_finished_at = None
                order.save()
                updated += 1
        self.message_user(request, f"Возвращено в работу: {updated} заказ(ов)")
    revert_to_in_progress.short_description = "Отменить отправку на проверку (вернуть в работу)"


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("description", "order", "status")
    list_filter = ("status",)
    search_fields = ("description", "order__code")
    ordering = ("status", "id")
