"""
Сервис для отправки сообщений в Telegram.
Использует unified TelegramSettings из telegram_bot.
"""
import requests

from apps.telegram_bot.models import TelegramSettings


class TelegramService:
    """Сервис для отправки уведомлений в Telegram."""

    def __init__(self):
        settings = TelegramSettings.objects.filter(
            is_active=True
        ).first()

        self.token = settings.bot_token if settings else None
        self.chat_id = settings.chat_id if settings else None
        self.settings = settings

    def send_message(self, text, thread_id=None):
        """
        Отправить сообщение в Telegram.

        Args:
            text: текст сообщения
            thread_id: ID темы (message_thread_id) для отправки в конкретную тему
                      Если None — отправка в общую группу
        """
        if not self.token or not self.chat_id:
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }

        # Добавляем message_thread_id если передан
        if thread_id not in (None, ''):
            try:
                payload["message_thread_id"] = int(thread_id)
            except (TypeError, ValueError):
                payload["message_thread_id"] = thread_id

        try:
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def send_order_message(self, text):
        """Отправить сообщение в тему Заказы."""
        thread_id = self.settings.orders_thread_id if self.settings else None
        return self.send_message(text, thread_id=thread_id)

    def send_expense_message(self, text):
        """Отправить сообщение в тему Расходы."""
        thread_id = self.settings.expenses_thread_id if self.settings else None
        return self.send_message(text, thread_id=thread_id)

    def send_completed_message(self, text):
        """Отправить сообщение в тему Завершённые заказы."""
        thread_id = self.settings.completed_thread_id if self.settings else None
        return self.send_message(text, thread_id=thread_id)

    def send_alert_message(self, text):
        """Отправить сообщение в тему Алерты."""
        thread_id = self.settings.alerts_thread_id if self.settings else None
        return self.send_message(text, thread_id=thread_id)

    def send_cleaner_message(self, text):
        """Отправить сообщение в тему Клинеры."""
        thread_id = self.settings.cleaner_thread_id if self.settings else None
        return self.send_message(text, thread_id=thread_id)

    def send_status_change_message(self, text):
        """Отправить сообщение в тему Изменений статуса."""
        thread_id = self.settings.status_changes_thread_id if self.settings else None
        return self.send_message(text, thread_id=thread_id)
