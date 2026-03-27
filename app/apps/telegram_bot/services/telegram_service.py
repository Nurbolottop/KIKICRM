"""Telegram notification service for CRM KIKI."""
import os
import requests
from django.conf import settings


def get_telegram_config():
    """
    Получает настройки Telegram из БД или ENV.
    
    Priority:
    1. Active TelegramSettings from DB
    2. ENV variables (TELEGRAM_BOT_TOKEN, TELEGRAM_GROUP_ID)
    3. Django settings
    
    Returns:
        dict or None: {
            'token': str,
            'chat_id': str,
            'notifications_new_order': bool,
            'notifications_new_expense': bool,
            'notifications_expense_approved': bool,
            'notifications_expense_rejected': bool,
            'orders_thread_id': str,
            'expenses_thread_id': str,
            'completed_thread_id': str,
            'alerts_thread_id': str,
            'cleaner_thread_id': str,
        }
    """

    
    config = {
        'token': None,
        'chat_id': None,
        'notifications_new_order': True,
        'notifications_new_expense': True,
        'notifications_expense_approved': True,
        'notifications_expense_rejected': True,
        'orders_thread_id': None,
        'expenses_thread_id': None,
        'completed_thread_id': None,
        'alerts_thread_id': None,
        'cleaner_thread_id': None,
    }
    
    # Try to get from DB first
    try:
        from .models import TelegramSettings
        settings_obj = TelegramSettings.objects.filter(is_active=True).first()
        
        if settings_obj and settings_obj.bot_token and settings_obj.chat_id:
            config['token'] = settings_obj.bot_token
            config['chat_id'] = settings_obj.chat_id
            config['notifications_new_order'] = settings_obj.notifications_new_order
            config['notifications_new_expense'] = settings_obj.notifications_new_expense
            config['notifications_expense_approved'] = settings_obj.notifications_expense_approved
            config['notifications_expense_rejected'] = settings_obj.notifications_expense_rejected
            config['orders_thread_id'] = settings_obj.orders_thread_id or None
            config['expenses_thread_id'] = settings_obj.expenses_thread_id or None
            config['completed_thread_id'] = settings_obj.completed_thread_id or None
            config['alerts_thread_id'] = settings_obj.alerts_thread_id or None
            config['cleaner_thread_id'] = settings_obj.cleaner_thread_id or None
            return config
    except Exception:
        # DB not available or table doesn't exist yet
        pass
    
    # Fallback to ENV / Django settings
    config['token'] = os.getenv(
        'TELEGRAM_BOT_TOKEN',
        getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    )
    config['chat_id'] = os.getenv(
        'TELEGRAM_CHAT_ID',
        getattr(settings, 'TELEGRAM_CHAT_ID', None)
    )
    
    if config['token'] and config['chat_id']:
        return config
    
    return None


def send_telegram_message(text, thread_id=None):
    """
    Отправляет сообщение в Telegram группу.
    
    Args:
        text: HTML текст сообщения
        thread_id: ID темы (message_thread_id) для отправки в конкретную тему
    
    Returns:
        bool: True если отправлено успешно, False если ошибка
    """
    config = get_telegram_config()
    
    if not config:
        print("[Telegram] Warning: Telegram not configured")
        return False
    
    token = config['token']
    chat_id = config['chat_id']
    
    if not token or not chat_id:
        print("[Telegram] Warning: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        # Add message_thread_id if provided
        if thread_id not in (None, ''):
            try:
                payload["message_thread_id"] = int(thread_id)
            except (TypeError, ValueError):
                payload["message_thread_id"] = thread_id
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return True
        else:
            print(f"[Telegram] Error: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"[Telegram] Request error: {e}")
        return False
    except Exception as e:
        print(f"[Telegram] Unexpected error: {e}")
        return False


def notify_new_order(order):
    """Отправляет уведомление о новом заказе в тему Заказы."""
    config = get_telegram_config()
    if not config or not config.get('notifications_new_order'):
        return False
    
    text = (
        f"🧹 <b>Новый заказ</b>\n\n"
        f"Клиент: {order.client.name}\n"
        f"Услуга: {order.service.name}\n"
        f"Адрес: {order.address}\n"
        f"Дата: {order.scheduled_date.strftime('%d.%m.%Y')} {order.scheduled_time.strftime('%H:%M')}\n"
        f"Цена: {order.price} сом"
    )
    return send_telegram_message(text, thread_id=config.get('orders_thread_id'))


def notify_new_expense(expense):
    """Отправляет уведомление о новом расходе в тему Расходы."""
    config = get_telegram_config()
    if not config or not config.get('notifications_new_expense'):
        return False
    
    text = (
        f"💰 <b>Новый расход</b>\n\n"
        f"Сотрудник: {expense.user.full_name}\n"
        f"Категория: {expense.get_category_display()}\n"
        f"Сумма: {expense.amount} сом\n"
        f"Описание: {expense.description or '—'}"
    )
    return send_telegram_message(text, thread_id=config.get('expenses_thread_id'))


def notify_expense_approved(expense):
    """Отправляет уведомление об одобренном расходе в тему Расходы."""
    config = get_telegram_config()
    if not config or not config.get('notifications_expense_approved'):
        return False
    
    text = (
        f"✅ <b>Расход одобрен</b>\n\n"
        f"Сотрудник: {expense.user.full_name}\n"
        f"Сумма: {expense.amount} сом\n"
        f"Категория: {expense.get_category_display()}"
    )
    return send_telegram_message(text, thread_id=config.get('expenses_thread_id'))


def notify_expense_rejected(expense):
    """Отправляет уведомление об отклоненном расходе в тему Алерты."""
    config = get_telegram_config()
    if not config or not config.get('notifications_expense_rejected'):
        return False
    
    text = (
        f"❌ <b>Расход отклонен</b>\n\n"
        f"Сотрудник: {expense.user.full_name}\n"
        f"Сумма: {expense.amount} сом\n"
        f"Категория: {expense.get_category_display()}"
    )
    return send_telegram_message(text, thread_id=config.get('alerts_thread_id'))


def notify_cleaner_confirmed(order_employee):
    """Отправляет уведомление о подтверждении участия клинером в тему Клинеры."""
    config = get_telegram_config()
    if not config:
        return False
    
    text = (
        f"✅ <b>Клинер подтвердил заказ</b>\n\n"
        f"Заказ: {order_employee.order.order_code}\n"
        f"Клинер: {order_employee.employee.user.full_name}\n"
        f"Клиент: {order_employee.order.client.name}\n"
        f"Дата: {order_employee.order.scheduled_date.strftime('%d.%m.%Y')} {order_employee.order.scheduled_time.strftime('%H:%M')}"
    )
    return send_telegram_message(text, thread_id=config.get('cleaner_thread_id'))


def notify_work_started(order_employee):
    """Отправляет уведомление о начале работы в тему Клинеры."""
    config = get_telegram_config()
    if not config:
        return False
    
    text = (
        f"▶ <b>Клинер начал работу</b>\n\n"
        f"Заказ: {order_employee.order.order_code}\n"
        f"Клинер: {order_employee.employee.user.full_name}\n"
        f"Клиент: {order_employee.order.client.name}\n"
        f"Адрес: {order_employee.order.address}\n"
        f"Время начала: {order_employee.started_at.strftime('%H:%M')}"
    )
    return send_telegram_message(text, thread_id=config.get('cleaner_thread_id'))


def notify_work_finished(order_employee):
    """Отправляет уведомление о завершении работы в тему Клинеры."""
    config = get_telegram_config()
    if not config:
        return False
    
    duration = ""
    if order_employee.started_at and order_employee.finished_at:
        from datetime import timedelta
        diff = order_employee.finished_at - order_employee.started_at
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        duration = f"\nДлительность: {hours}ч {minutes}мин"
    
    text = (
        f"🏁 <b>Клинер завершил работу</b>\n\n"
        f"Заказ: {order_employee.order.order_code}\n"
        f"Клинер: {order_employee.employee.user.full_name}\n"
        f"Клиент: {order_employee.order.client.name}\n"
        f"Время завершения: {order_employee.finished_at.strftime('%H:%M')}"
        f"{duration}"
    )
    return send_telegram_message(text, thread_id=config.get('cleaner_thread_id'))
