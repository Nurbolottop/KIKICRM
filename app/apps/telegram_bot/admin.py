from django.contrib import admin
from .models import TelegramSettings, ClientBotSettings


@admin.register(TelegramSettings)
class TelegramSettingsAdmin(admin.ModelAdmin):
    """Админ-панель для настроек Telegram (Unified)."""
    
    list_display = [
        'id',
        'is_active',
        'get_masked_token',
        'chat_id',
        'orders_thread_id',
        'status_changes_thread_id',
        'expenses_thread_id',
        'completed_thread_id',
        'updated_at'
    ]
    
    list_editable = [
        'is_active',
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основное', {
            'fields': ('is_active', 'bot_token', 'chat_id'),
            'description': 'Настройте токен бота и ID группы. Только одна запись должна быть активной.'
        }),
        ('Темы / Topics', {
            'fields': (
                'orders_thread_id',
                'status_changes_thread_id',
                'expenses_thread_id',
                'completed_thread_id',
                'alerts_thread_id',
                'cleaner_thread_id',
            ),
            'description': (
                'ID тем (message_thread_id) для отправки уведомлений в конкретные темы группы. '
                'Если поле пустое — уведомление отправляется в общую группу.'
            )
        }),
        ('Типы уведомлений (Legacy)', {
            'fields': (
                'notifications_new_order',
                'notifications_new_expense',
                'notifications_expense_approved',
                'notifications_expense_rejected'
            ),
            'classes': ('collapse',)
        }),
        ('Системное', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_masked_token(self, obj):
        """Отображает замаскированный токен."""
        return obj.get_masked_token()
    get_masked_token.short_description = 'Токен (маскированный)'


@admin.register(ClientBotSettings)
class ClientBotSettingsAdmin(admin.ModelAdmin):
    """Админ-панель для настроек бота клиентов."""
    
    list_display = [
        'id',
        'is_active',
        'get_masked_token',
        'bot_username',
        'updated_at'
    ]
    
    list_editable = ['is_active']
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основное', {
            'fields': ('is_active', 'bot_token', 'bot_username'),
            'description': 'Настройте токен бота для клиентов. Получите токен от @BotFather.'
        }),
        ('Системное', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_masked_token(self, obj):
        """Отображает замаскированный токен."""
        return obj.get_masked_token()
    get_masked_token.short_description = 'Токен (маскированный)'
