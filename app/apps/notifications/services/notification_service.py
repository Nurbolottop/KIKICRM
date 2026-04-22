"""
Сервис для отправки различных типов уведомлений.
"""
from apps.notifications.services.telegram_service import TelegramService


# Русские названия месяцев
RUSSIAN_MONTHS = {
    1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
    5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
    9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
}


def format_date_russian(date_obj):
    """Форматирует дату с русским названием месяца."""
    if not date_obj:
        return '—'
    return f"{date_obj.day} {RUSSIAN_MONTHS.get(date_obj.month, '')}"


class NotificationService:
    """Сервис для отправки уведомлений о событиях CRM."""

    @staticmethod
    def new_order(order):
        """Уведомление о создании нового заказа."""

        # Format date
        scheduled_date = format_date_russian(order.scheduled_date)
        scheduled_time = order.scheduled_time.strftime('%H:%M') if order.scheduled_time else '—'
        
        # Client info
        client = order.client
        client_name = client.get_full_name() if client else '—'
        client_phone = client.phone if client else '—'
        client_address = order.address if hasattr(order, 'address') and order.address else (
            client.address if hasattr(client, 'address') and client.address else '—'
        )
        
        # Service info
        service_name = order.service.name if order.service else '—'
        
        # Room info - use rooms_count instead of room_count
        rooms_count = order.rooms_count if hasattr(order, 'rooms_count') and order.rooms_count else '—'
        area = order.area if hasattr(order, 'area') and order.area else '—'
        room_info = f"{rooms_count} комнат" if rooms_count != '—' else (f"{area} кв.м" if area != '—' else '—')
        
        # Property type display
        property_type_display = order.get_property_type_display() if hasattr(order, 'get_property_type_display') else 'квартира'
        
        # Extra services from order.work_scope or order.extra_services
        extra_services = order.work_scope if hasattr(order, 'work_scope') and order.work_scope else 'Нет'
        
        # Notes from order.comment
        notes = order.comment if hasattr(order, 'comment') and order.comment else '—'
        
        # Payment method
        payment_method = order.payment_method if hasattr(order, 'payment_method') and order.payment_method else 'наличка'
        
        # Prepayment (Задаток)
        prepayment = order.prepayment_amount if hasattr(order, 'prepayment_amount') and order.prepayment_amount else None
        
        # Price - show preliminary_price if set, otherwise final price, otherwise calculate on site
        preliminary = order.preliminary_price if hasattr(order, 'preliminary_price') and order.preliminary_price and order.preliminary_price > 0 else None
        final_price = order.price if hasattr(order, 'price') and order.price and order.price > 0 else None
        
        if preliminary:
            price_text = f"{preliminary} сом (предварительно)"
        elif final_price:
            price_text = f"{final_price} сом"
        else:
            price_text = "Сумму посчитать на месте"
        
        # Order code
        order_code = order.order_code if order.order_code else f"#{order.id}"

        # Доп. услуги из order_extra_services
        try:
            extra_services_qs = order.order_extra_services.select_related('extra_service').all()
            if extra_services_qs.exists():
                extra_lines = '\n'.join(
                    f"  — {oes.extra_service.name} × {oes.quantity}"
                    f"{' (' + str(oes.extra_service.price) + ' сом)' if oes.extra_service.price else ''}"
                    for oes in extra_services_qs
                )
            else:
                extra_lines = extra_services or 'Нет'
        except Exception:
            extra_lines = extra_services or 'Нет'

        # Определяем: это химчистка/доп.услуга или обычная уборка
        is_extra_only = order.service and getattr(order.service, 'is_extra_only', False)

        if is_extra_only:
            # ── Блок для Химчистки / доп. услуг ───────────────
            text = f"""
🧺 <b>Заказ {order_code}</b>

<b>Клиент:</b>
• ФИО: {client_name}
• Телефон: {client_phone}
• Адрес: {client_address}

<b>🗓 Дата и время:</b> {scheduled_date}, {scheduled_time}

<b>Услуга:</b>
• Тип: {service_name}
• Доп. услуги:
{extra_lines}
• Особые пожелания: {notes}

<b>Оплата:</b>
• Способ: {payment_method}
{f"• Задаток: {prepayment} сом" if prepayment else ""}

💰 <b>Итоговая сумма: {price_text}</b>

⚠️ <b>Примечание:</b>
1. Клиент должен проверить работу сразу после выполнения. Жалобы после ухода клинеров не принимаются.

2. Оплату строго давать менеджеру если наличка, если перевод на номер мбанк +996 221 241 172 Кишимжан К и чек оператору.
"""
        else:
            # ── Блок для обычной уборки ────────────────────────
            text = f"""
🆕 <b>Заказ {order_code}</b>

<b>Клиент:</b>
• ФИО: {client_name}
• Телефон: {client_phone}
• Адрес: {client_address}

<b>Детали уборки:</b>
• Дата и время: {scheduled_date}, {scheduled_time}
• Вид помещения: {property_type_display}
• Комнаты: {rooms_count if rooms_count != '—' else '—'}
• Площадь: {area if area != '—' else '—'} м²
• Санузлы: {order.bathrooms_count if hasattr(order, 'bathrooms_count') and order.bathrooms_count else '—'}
• Окна: {order.windows_count if hasattr(order, 'windows_count') and order.windows_count else '—'}
• После ремонта: {"Да" if hasattr(order, 'after_renovation') and order.after_renovation else "Нет"}

<b>Услуги:</b>
• Основная: {service_name}
• Доп.услуги:
{extra_lines}
• Особые пожелания: {notes}

<b>Оплата:</b>
• Способ: {payment_method}
{f"• Задаток: {prepayment} сом" if prepayment else ""}

💰 <b>Итоговая сумма: {price_text}</b>

⚠️ <b>Примечание:</b>
1. Клиент должен проверить работу сразу после уборки. Жалобы после ухода клинеров не принимаются.

2. В доме, в квартире и в объекте должна быть вода, в каждой комнате должен быть свет.

3. Оплату строго давать менеджеру если наличка, если перевод на номер мбанк +996 221 241 172 Кишимжан К и чек оператору.
"""
        TelegramService().send_order_message(text)

    @staticmethod
    def order_completed(order):
        """Уведомление о завершении заказа."""

        text = f"""
✅ <b>Заказ завершён</b>

Код: {order.order_code}
Клиент: {order.client.get_full_name()}
"""
        TelegramService().send_completed_message(text)

    @staticmethod
    def expense_created(expense):
        """Уведомление о создании нового расхода."""
        text = f"""
💰 <b>Новый расход</b>

Категория: {expense.category.name if expense.category else 'Без категории'}
Сумма: {expense.amount} сом
Описание: {expense.description[:100]}
"""
        TelegramService().send_expense_message(text)

    @staticmethod
    def expense_approved(expense):
        """Уведомление об одобрении расхода."""
        text = f"""
✅ <b>Расход одобрен</b>

Категория: {expense.category.name if expense.category else 'Без категории'}
Сумма: {expense.amount} сом
Одобрил: {expense.approved_by.get_full_name() if expense.approved_by else '—'}
"""
        TelegramService().send_expense_message(text)

    @staticmethod
    def cleaner_refused(order_employee):
        """Уведомление об отказе клинера от заказа."""
        text = f"""
⚠️ <b>Клинер отказался от заказа</b>

Заказ: {order_employee.order.order_code}
Клиент: {order_employee.order.client.get_full_name()}
Клинер: {order_employee.employee.user.get_full_name()}
Причина: {order_employee.refuse_reason or 'Не указана'}
"""
        TelegramService().send_alert_message(text)

    @staticmethod
    def cleaner_confirmed(order_employee):
        """Уведомление о подтверждении заказа клинером."""
        text = f"""
👍 <b>Клинер подтвердил заказ</b>

Заказ: {order_employee.order.order_code}
Клиент: {order_employee.order.client.get_full_name()}
Клинер: {order_employee.employee.user.get_full_name()}
"""
        TelegramService().send_cleaner_message(text)

    @staticmethod
    def cleaner_started_work(order_employee):
        """Уведомление о начале работы клинера."""
        text = f"""
🚀 <b>Клинер начал работу</b>

Заказ: {order_employee.order.order_code}
Клиент: {order_employee.order.client.get_full_name()}
Клинер: {order_employee.employee.user.get_full_name()}
"""
        TelegramService().send_cleaner_message(text)

    @staticmethod
    def cleaner_finished_work(order_employee):
        """Уведомление о завершении работы клинера."""
        text = f"""
🏁 <b>Клинер завершил работу</b>

Заказ: {order_employee.order.order_code}
Клиент: {order_employee.order.client.get_full_name()}
Клинер: {order_employee.employee.user.get_full_name()}
"""
        TelegramService().send_cleaner_message(text)
