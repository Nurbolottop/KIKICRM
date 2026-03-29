from django.db import models


class TelegramSettings(models.Model):
    """Настройки Telegram бота для уведомлений CRM (Unified)."""
    
    is_active = models.BooleanField(
        'Активно',
        default=True,
        help_text='Только одна запись должна быть активной'
    )
    
    bot_token = models.CharField(
        'Токен бота',
        max_length=255,
        blank=True,
        help_text='Токен Telegram бота от @BotFather'
    )
    
    chat_id = models.CharField(
        'ID группы/чата',
        max_length=100,
        blank=True,
        help_text='ID Telegram группы или чата для уведомлений'
    )
    
    # Thread/Topic IDs for different event types
    orders_thread_id = models.CharField(
        'ID темы заказов',
        max_length=100,
        blank=True,
        help_text='ID темы Telegram для заказов'
    )
    
    expenses_thread_id = models.CharField(
        'ID темы расходов',
        max_length=100,
        blank=True,
        help_text='ID темы Telegram для расходов'
    )
    
    completed_thread_id = models.CharField(
        'ID темы завершённых заказов',
        max_length=100,
        blank=True,
        help_text='ID темы Telegram для завершённых заказов'
    )
    
    alerts_thread_id = models.CharField(
        'ID темы алертов',
        max_length=100,
        blank=True,
        help_text='ID темы Telegram для алертов и отказов'
    )
    
    cleaner_thread_id = models.CharField(
        'Уведомления',
        max_length=100,
        blank=True,
        help_text='ID темы Telegram для всех уведомлений системы (статусы, назначения, клинеры)'
    )
    
    status_changes_thread_id = models.CharField(
        'ID темы изменений статуса',
        max_length=100,
        blank=True,
        help_text='ID темы Telegram для уведомлений об изменении статуса заказов'
    )
    
    reviews_thread_id = models.CharField(
        'ID темы отзывов',
        max_length=100,
        blank=True,
        help_text='ID темы Telegram для отзывов клиентов'
    )
    
    # Legacy notification flags (for backward compatibility)
    notifications_new_order = models.BooleanField(
        'Новый заказ',
        default=True,
        help_text='Отправлять уведомление при создании заказа'
    )
    
    notifications_new_expense = models.BooleanField(
        'Новый расход',
        default=True,
        help_text='Отправлять уведомление при создании расхода'
    )
    
    notifications_expense_approved = models.BooleanField(
        'Расход одобрен',
        default=True,
        help_text='Отправлять уведомление при одобрении расхода'
    )
    
    notifications_expense_rejected = models.BooleanField(
        'Расход отклонен',
        default=True,
        help_text='Отправлять уведомление при отклонении расхода'
    )
    
    created_at = models.DateTimeField(
        'Дата создания',
        auto_now_add=True
    )
    
    updated_at = models.DateTimeField(
        'Дата обновления',
        auto_now=True
    )
    
    class Meta:
        verbose_name = 'Настройки Telegram'
        verbose_name_plural = 'Настройки Telegram'
    
    def __str__(self):
        return f'Telegram Settings #{self.id} ({"Active" if self.is_active else "Inactive"})'
    
    def get_masked_token(self):
        """Возвращает замаскированный токен для отображения."""
        if not self.bot_token:
            return '—'
        parts = self.bot_token.split(':')
        if len(parts) == 2:
            return f'{parts[0]}:***{parts[1][-3:]}'
        return f'{self.bot_token[:10]}***'
    
    def get_telegram_config(self):
        """
        Возвращает конфигурацию для Telegram в виде словаря.
        
        Returns:
            dict: словарь с token, chat_id и thread_id для разных типов событий
        """
        return {
            'token': self.bot_token,
            'chat_id': self.chat_id,
            'orders_thread_id': self.orders_thread_id or None,
            'expenses_thread_id': self.expenses_thread_id or None,
            'completed_thread_id': self.completed_thread_id or None,
            'alerts_thread_id': self.alerts_thread_id or None,
            'cleaner_thread_id': self.cleaner_thread_id or None,
            'status_changes_thread_id': self.status_changes_thread_id or None,
        }


class ClientBotSettings(models.Model):
    """Настройки Telegram бота для клиентов."""

    is_active = models.BooleanField(
        'Активно',
        default=True,
        help_text='Бот будет обрабатывать сообщения только если активен'
    )

    bot_token = models.CharField(
        'Токен бота',
        max_length=255,
        blank=True,
        help_text='Токен Telegram бота для клиентов от @BotFather'
    )

    bot_username = models.CharField(
        'Username бота',
        max_length=255,
        blank=True,
        help_text='Например: @KikiClientBot'
    )

    created_at = models.DateTimeField(
        'Дата создания',
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        'Дата обновления',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Настройки бота для клиентов'
        verbose_name_plural = 'Настройки бота для клиентов'

    def __str__(self):
        status = 'Active' if self.is_active else 'Inactive'
        return f'Client Bot Settings #{self.id} ({status})'

    def get_masked_token(self):
        """Возвращает замаскированный токен для отображения."""
        if not self.bot_token:
            return '—'
        parts = self.bot_token.split(':')
        if len(parts) == 2:
            return f'{parts[0]}:***{parts[1][-3:]}'
        return f'{self.bot_token[:10]}***'
