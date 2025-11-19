"""
Обработчики команд для клинеров
"""
from telebot import types
from django.utils import timezone
from django.db import models
from apps.orders.models import Order, Task
from apps.users.models import User
from .models import TelegramUser
import logging

logger = logging.getLogger(__name__)


def get_client_full_name(client):
    """Получить полное имя клиента"""
    if client.last_name:
        return f"{client.first_name} {client.last_name}"
    return client.first_name


def get_cleaner_keyboard():
    """Клавиатура для клинера"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton('📋 Мои заказы')
    btn2 = types.KeyboardButton('🆕 Новые заказы')
    btn3 = types.KeyboardButton('⏰ Текущий заказ')
    btn4 = types.KeyboardButton('✅ Завершенные')
    btn5 = types.KeyboardButton('👤 Профиль')
    btn6 = types.KeyboardButton('📊 Статистика')
    btn7 = types.KeyboardButton('🚪 Выйти')
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    markup.add(btn7)
    return markup


def get_order_actions_keyboard(order_id, is_senior=False):
    """Клавиатура действий с заказом"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if is_senior:
        btn_accept = types.InlineKeyboardButton('✅ Принять', callback_data=f'order_accept_{order_id}')
        btn_decline = types.InlineKeyboardButton('❌ Отказаться', callback_data=f'order_decline_{order_id}')
        btn_start = types.InlineKeyboardButton('▶️ Начать работу', callback_data=f'order_start_{order_id}')
        btn_finish = types.InlineKeyboardButton('🏁 Завершить', callback_data=f'order_finish_{order_id}')
        btn_tasks = types.InlineKeyboardButton('📋 Задачи', callback_data=f'task_list_{order_id}')
        btn_details = types.InlineKeyboardButton('📄 Подробнее', callback_data=f'order_details_{order_id}')
        
        markup.add(btn_accept, btn_decline)
        markup.add(btn_start, btn_finish)
        markup.add(btn_tasks, btn_details)
    else:
        btn_details = types.InlineKeyboardButton('📄 Подробнее', callback_data=f'order_details_{order_id}')
        btn_photo = types.InlineKeyboardButton('📷 Загрузить фото', callback_data=f'order_photo_{order_id}')
        markup.add(btn_details, btn_photo)
    
    return markup


def format_order_info(order, detailed=False):
    """Форматирование информации о заказе"""
    status_emoji = {
        'ASSIGNED': '🆕',
        'ACCEPTED': '✅',
        'IN_PROGRESS': '⏰',
        'PENDING_REVIEW': '🔍',
        'COMPLETED': '✅',
        'DECLINED': '❌'
    }
    
    status = order.status_senior_cleaner or 'ASSIGNED'
    emoji = status_emoji.get(status, '📋')
    
    text = f"""
{emoji} <b>Заказ {order.code}</b>

<b>Клиент:</b> {get_client_full_name(order.client)}
<b>Телефон:</b> {order.client.phone}
<b>Адрес:</b> {order.address}
<b>Дата и время:</b> {order.date_time.strftime('%d.%m.%Y %H:%M')}
<b>Услуга:</b> {order.service.title if order.service else 'Не указано'}
<b>Статус:</b> {order.get_status_senior_cleaner_display() if order.status_senior_cleaner else 'Назначен'}
"""
    
    if detailed:
        text += f"""
<b>Тип помещения:</b> {order.get_property_type_display() if order.property_type else 'Не указано'}
<b>Объём работы:</b> {order.estimated_area or 'Не указано'}
<b>Стоимость:</b> {order.final_cost or order.estimated_cost or 'Не указано'} сом
"""
        
        if order.deadline:
            text += f"<b>Крайний срок:</b> {order.deadline.strftime('%d.%m.%Y %H:%M')}\n"
        
        if order.manager_comment:
            text += f"<b>Комментарий менеджера:</b> {order.manager_comment}\n"
        
        if order.notes:
            text += f"<b>Заметки клиента:</b> {order.notes}\n"
        
        # Информация о команде
        if order.senior_cleaner:
            text += f"\n<b>Старший клинер:</b> {order.senior_cleaner.full_name}\n"
        
        cleaners = order.cleaners.all()
        if cleaners:
            text += "<b>Команда клинеров:</b>\n"
            for cleaner in cleaners:
                text += f"  • {cleaner.full_name}\n"
        
        # Время работы
        if order.work_started_at:
            text += f"\n<b>Работа начата:</b> {order.work_started_at.strftime('%d.%m.%Y %H:%M')}\n"
        
        if order.work_finished_at:
            text += f"<b>Работа завершена:</b> {order.work_finished_at.strftime('%d.%m.%Y %H:%M')}\n"
            
            if order.work_started_at:
                duration = order.work_finished_at - order.work_started_at
                hours = duration.total_seconds() / 3600
                text += f"<b>Длительность:</b> {hours:.1f} ч\n"
    
    return text


def handle_my_orders(bot, message, telegram_user):
    """Обработчик 'Мои заказы'"""
    try:
        if not telegram_user.user:
            bot.send_message(
                message.chat.id,
                "❌ Ваш аккаунт не привязан к системе. Обратитесь к администратору."
            )
            return
        
        user = telegram_user.user
        
        # Получаем заказы в зависимости от роли
        if user.role == User.Role.SENIOR_CLEANER:
            orders = Order.objects.filter(
                senior_cleaner=user,
                status_senior_cleaner__in=['ASSIGNED', 'ACCEPTED', 'IN_PROGRESS']
            ).order_by('date_time')
        elif user.role == User.Role.CLEANER:
            orders = Order.objects.filter(
                cleaners=user,
                status_senior_cleaner__in=['ACCEPTED', 'IN_PROGRESS']
            ).order_by('date_time')
        else:
            bot.send_message(
                message.chat.id,
                "❌ У вас нет доступа к заказам."
            )
            return
        
        if not orders.exists():
            bot.send_message(
                message.chat.id,
                "📭 У вас пока нет активных заказов.",
                reply_markup=get_cleaner_keyboard()
            )
            return
        
        bot.send_message(
            message.chat.id,
            f"📋 <b>Ваши активные заказы ({orders.count()}):</b>",
            parse_mode='HTML'
        )
        
        is_senior = user.role == User.Role.SENIOR_CLEANER
        
        for order in orders[:10]:  # Показываем максимум 10 заказов
            text = format_order_info(order)
            markup = get_order_actions_keyboard(order.id, is_senior)
            bot.send_message(
                message.chat.id,
                text,
                reply_markup=markup,
                parse_mode='HTML'
            )
        
        if orders.count() > 10:
            bot.send_message(
                message.chat.id,
                f"ℹ️ Показаны первые 10 заказов из {orders.count()}"
            )
            
    except Exception as e:
        import traceback
        logger.error(f"Ошибка в handle_my_orders: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        bot.send_message(
            message.chat.id,
            f"❌ Произошла ошибка при загрузке заказов.\n\n<code>{str(e)}</code>",
            parse_mode='HTML'
        )


def handle_new_orders(bot, message, telegram_user):
    """Обработчик 'Новые заказы'"""
    try:
        if not telegram_user.user:
            bot.send_message(
                message.chat.id,
                "❌ Ваш аккаунт не привязан к системе."
            )
            return
        
        user = telegram_user.user
        
        if user.role != User.Role.SENIOR_CLEANER:
            bot.send_message(
                message.chat.id,
                "❌ Только старшие клинеры могут просматривать новые заказы."
            )
            return
        
        # Новые назначенные заказы
        orders = Order.objects.filter(
            senior_cleaner=user,
            status_senior_cleaner='ASSIGNED'
        ).order_by('date_time')
        
        if not orders.exists():
            bot.send_message(
                message.chat.id,
                "📭 Нет новых назначенных заказов.",
                reply_markup=get_cleaner_keyboard()
            )
            return
        
        bot.send_message(
            message.chat.id,
            f"🆕 <b>Новые заказы ({orders.count()}):</b>",
            parse_mode='HTML'
        )
        
        for order in orders[:5]:
            text = format_order_info(order, detailed=True)
            markup = get_order_actions_keyboard(order.id, is_senior=True)
            bot.send_message(
                message.chat.id,
                text,
                reply_markup=markup,
                parse_mode='HTML'
            )
            
    except Exception as e:
        import traceback
        logger.error(f"Ошибка в handle_new_orders: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        bot.send_message(
            message.chat.id,
            f"❌ Произошла ошибка.\n\n<code>{str(e)}</code>",
            parse_mode='HTML'
        )


def handle_current_order(bot, message, telegram_user):
    """Обработчик 'Текущий заказ'"""
    try:
        if not telegram_user.user:
            bot.send_message(
                message.chat.id,
                "❌ Ваш аккаунт не привязан к системе."
            )
            return
        
        user = telegram_user.user
        
        # Ищем заказ в работе
        if user.role == User.Role.SENIOR_CLEANER:
            order = Order.objects.filter(
                senior_cleaner=user,
                status_senior_cleaner='IN_PROGRESS'
            ).first()
        elif user.role == User.Role.CLEANER:
            order = Order.objects.filter(
                cleaners=user,
                status_senior_cleaner='IN_PROGRESS'
            ).first()
        else:
            bot.send_message(message.chat.id, "❌ У вас нет доступа.")
            return
        
        if not order:
            # Показываем список принятых заказов, которые можно начать
            if user.role == User.Role.SENIOR_CLEANER:
                accepted_orders = Order.objects.filter(
                    senior_cleaner=user,
                    status_senior_cleaner='ACCEPTED'
                ).order_by('date_time')
                
                if accepted_orders.exists():
                    bot.send_message(
                        message.chat.id,
                        f"📭 У вас нет заказа в работе.\n\n✅ Принятые заказы ({accepted_orders.count()}):\nВыберите заказ для начала работы:",
                        parse_mode='HTML'
                    )
                    
                    for order in accepted_orders[:5]:
                        text = format_order_info(order)
                        markup = get_order_actions_keyboard(order.id, is_senior=True)
                        bot.send_message(
                            message.chat.id,
                            text,
                            reply_markup=markup,
                            parse_mode='HTML'
                        )
                    return
            
            bot.send_message(
                message.chat.id,
                "📭 У вас нет заказа в работе.",
                reply_markup=get_cleaner_keyboard()
            )
            return
        
        text = format_order_info(order, detailed=True)
        is_senior = user.role == User.Role.SENIOR_CLEANER
        markup = get_order_actions_keyboard(order.id, is_senior)
        
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=markup,
            parse_mode='HTML'
        )
        
        # Показываем задачи
        tasks = order.tasks.all()
        if tasks:
            bot.send_message(
                message.chat.id,
                "<b>📝 Задачи по заказу:</b>",
                parse_mode='HTML'
            )
            for task in tasks:
                task_text = f"""
{'✅' if task.status == 'DONE' else '⏳'} <b>{task.description}</b>
Статус: {task.get_status_display()}
Исполнитель: {task.cleaner.full_name if task.cleaner else 'Не назначен'}
"""
                if task.comment:
                    task_text += f"Комментарий: {task.comment}\n"
                
                bot.send_message(message.chat.id, task_text, parse_mode='HTML')
                
    except Exception as e:
        import traceback
        logger.error(f"Ошибка в handle_current_order: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        bot.send_message(
            message.chat.id,
            f"❌ Произошла ошибка.\n\n<code>{str(e)}</code>",
            parse_mode='HTML'
        )


def handle_completed_orders(bot, message, telegram_user):
    """Обработчик 'Завершенные'"""
    try:
        if not telegram_user.user:
            bot.send_message(message.chat.id, "❌ Ваш аккаунт не привязан к системе.")
            return
        
        user = telegram_user.user
        
        if user.role == User.Role.SENIOR_CLEANER:
            orders = Order.objects.filter(
                senior_cleaner=user,
                status_senior_cleaner='COMPLETED'
            ).order_by('-work_finished_at')[:10]
        elif user.role == User.Role.CLEANER:
            orders = Order.objects.filter(
                cleaners=user,
                status_senior_cleaner='COMPLETED'
            ).order_by('-work_finished_at')[:10]
        else:
            bot.send_message(message.chat.id, "❌ У вас нет доступа.")
            return
        
        if not orders.exists():
            bot.send_message(
                message.chat.id,
                "📭 Нет завершенных заказов.",
                reply_markup=get_cleaner_keyboard()
            )
            return
        
        bot.send_message(
            message.chat.id,
            f"✅ <b>Завершенные заказы (последние 10):</b>",
            parse_mode='HTML'
        )
        
        for order in orders:
            text = format_order_info(order, detailed=True)
            bot.send_message(message.chat.id, text, parse_mode='HTML')
            
    except Exception as e:
        import traceback
        logger.error(f"Ошибка в handle_completed_orders: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        bot.send_message(
            message.chat.id,
            f"❌ Произошла ошибка.\n\n<code>{str(e)}</code>",
            parse_mode='HTML'
        )


def handle_cleaner_profile(bot, message, telegram_user):
    """Обработчик 'Профиль' для клинера"""
    try:
        if not telegram_user.user:
            bot.send_message(message.chat.id, "❌ Ваш аккаунт не привязан к системе.")
            return
        
        user = telegram_user.user
        
        # Статистика
        if user.role == User.Role.SENIOR_CLEANER:
            total_orders = Order.objects.filter(senior_cleaner=user).count()
            completed = Order.objects.filter(
                senior_cleaner=user,
                status_senior_cleaner='COMPLETED'
            ).count()
            in_progress = Order.objects.filter(
                senior_cleaner=user,
                status_senior_cleaner='IN_PROGRESS'
            ).count()
        else:
            total_orders = Order.objects.filter(cleaners=user).count()
            completed = Order.objects.filter(
                cleaners=user,
                status_senior_cleaner='COMPLETED'
            ).count()
            in_progress = Order.objects.filter(
                cleaners=user,
                status_senior_cleaner='IN_PROGRESS'
            ).count()
        
        profile_text = f"""
👤 <b>Мой профиль</b>

<b>ФИО:</b> {user.full_name}
<b>Роль:</b> {user.get_role_display()}
<b>Статус:</b> {user.get_status_display()}
<b>Телефон:</b> {user.phone or 'Не указан'}
<b>Дата найма:</b> {user.hire_date.strftime('%d.%m.%Y') if user.hire_date else 'Не указана'}

📊 <b>Статистика:</b>
• Всего заказов: {total_orders}
• Завершено: {completed}
• В работе: {in_progress}

💰 <b>Оплата:</b>
• Тип: {user.get_payment_type_display()}
• Ставка: {user.rate or 'Не указана'} сом
"""
        
        if user.is_on_shift:
            profile_text += "\n🟢 <b>Статус:</b> На смене"
        else:
            profile_text += "\n⚪ <b>Статус:</b> Не на смене"
        
        if user.is_available:
            profile_text += " | Свободен"
        else:
            profile_text += " | Занят"
        
        bot.send_message(
            message.chat.id,
            profile_text,
            parse_mode='HTML',
            reply_markup=get_cleaner_keyboard()
        )
        
    except Exception as e:
        import traceback
        logger.error(f"Ошибка в handle_cleaner_profile: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        bot.send_message(
            message.chat.id,
            f"❌ Произошла ошибка.\n\n<code>{str(e)}</code>",
            parse_mode='HTML'
        )


def handle_cleaner_stats(bot, message, telegram_user):
    """Обработчик 'Статистика' для клинера"""
    try:
        if not telegram_user.user:
            bot.send_message(message.chat.id, "❌ Ваш аккаунт не привязан к системе.")
            return
        
        user = telegram_user.user
        
        # Получаем статистику
        if user.role == User.Role.SENIOR_CLEANER:
            all_orders = Order.objects.filter(senior_cleaner=user)
        else:
            all_orders = Order.objects.filter(cleaners=user)
        
        total = all_orders.count()
        completed = all_orders.filter(status_senior_cleaner='COMPLETED').count()
        in_progress = all_orders.filter(status_senior_cleaner='IN_PROGRESS').count()
        pending = all_orders.filter(status_senior_cleaner='PENDING_REVIEW').count()
        declined = all_orders.filter(status_senior_cleaner='DECLINED').count()
        
        # Средняя оценка
        avg_rating = all_orders.filter(
            quality_rating__isnull=False
        ).aggregate(models.Avg('quality_rating'))['quality_rating__avg']
        
        stats_text = f"""
📊 <b>Статистика работы</b>

<b>Всего заказов:</b> {total}
✅ Завершено: {completed}
⏰ В работе: {in_progress}
🔍 На проверке: {pending}
❌ Отклонено: {declined}
"""
        
        if avg_rating:
            stars = '⭐' * int(avg_rating)
            stats_text += f"\n<b>Средняя оценка:</b> {stars} ({avg_rating:.1f}/5)"
        
        # Статистика за текущий месяц
        from django.db.models import Count
        from datetime import datetime, timedelta
        
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0)
        month_orders = all_orders.filter(created_at__gte=month_start)
        month_completed = month_orders.filter(status_senior_cleaner='COMPLETED').count()
        
        stats_text += f"""

📅 <b>За текущий месяц:</b>
• Всего заказов: {month_orders.count()}
• Завершено: {month_completed}
"""
        
        bot.send_message(
            message.chat.id,
            stats_text,
            parse_mode='HTML',
            reply_markup=get_cleaner_keyboard()
        )
        
    except Exception as e:
        import traceback
        logger.error(f"Ошибка в handle_cleaner_stats: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        bot.send_message(
            message.chat.id,
            f"❌ Произошла ошибка.\n\n<code>{str(e)}</code>",
            parse_mode='HTML'
        )
