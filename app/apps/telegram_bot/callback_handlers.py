"""
Обработчики callback-кнопок для клинеров
"""
from telebot import types
from django.utils import timezone
from apps.orders.models import Order
from apps.users.models import User
from .models import TelegramUser
from .cleaner_handlers import get_client_full_name
import logging

logger = logging.getLogger(__name__)


def handle_order_accept(bot, call, telegram_user):
    """Принятие заказа старшим клинером"""
    try:
        order_id = int(call.data.split('_')[-1])
        order = Order.objects.get(id=order_id)
        
        if not telegram_user.user or telegram_user.user != order.senior_cleaner:
            bot.answer_callback_query(call.id, "❌ У вас нет прав на это действие")
            return
        
        if order.status_senior_cleaner != 'ASSIGNED':
            bot.answer_callback_query(call.id, "❌ Заказ уже обработан")
            return
        
        # Принимаем заказ
        order.status_senior_cleaner = 'ACCEPTED'
        order.save()
        
        bot.answer_callback_query(call.id, "✅ Заказ принят!")
        
        # Обновляем сообщение
        text = f"""
✅ <b>Заказ {order.code} ПРИНЯТ</b>

<b>Клиент:</b> {get_client_full_name(order.client)}
<b>Адрес:</b> {order.address}
<b>Дата и время:</b> {order.date_time.strftime('%d.%m.%Y %H:%M')}

Теперь вы можете начать работу над заказом.
"""
        
        markup = types.InlineKeyboardMarkup()
        btn_start = types.InlineKeyboardButton('▶️ Начать работу', callback_data=f'order_start_{order.id}')
        btn_details = types.InlineKeyboardButton('📄 Подробнее', callback_data=f'order_details_{order.id}')
        markup.add(btn_start, btn_details)
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='HTML'
        )
        
        # Уведомляем менеджера (если нужно)
        logger.info(f"Заказ {order.code} принят клинером {telegram_user.user.full_name}")
        
    except Order.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Заказ не найден")
    except Exception as e:
        logger.error(f"Ошибка в handle_order_accept: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


def handle_order_decline(bot, call, telegram_user):
    """Отказ от заказа"""
    try:
        order_id = int(call.data.split('_')[-1])
        order = Order.objects.get(id=order_id)
        
        if not telegram_user.user or telegram_user.user != order.senior_cleaner:
            bot.answer_callback_query(call.id, "❌ У вас нет прав на это действие")
            return
        
        if order.status_senior_cleaner not in ['ASSIGNED', 'ACCEPTED']:
            bot.answer_callback_query(call.id, "❌ Нельзя отказаться от заказа в этом статусе")
            return
        
        # Запрашиваем причину отказа
        bot.answer_callback_query(call.id, "Укажите причину отказа")
        
        msg = bot.send_message(
            call.message.chat.id,
            f"❌ <b>Отказ от заказа {order.code}</b>\n\nУкажите причину отказа:",
            parse_mode='HTML'
        )
        
        # Сохраняем ID заказа для следующего шага
        bot.register_next_step_handler(msg, lambda m: process_decline_reason(bot, m, order, telegram_user))
        
    except Order.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Заказ не найден")
    except Exception as e:
        logger.error(f"Ошибка в handle_order_decline: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


def process_decline_reason(bot, message, order, telegram_user):
    """Обработка причины отказа"""
    try:
        reason = message.text
        
        order.status_senior_cleaner = 'DECLINED'
        order.decline_reason = reason
        order.save()
        
        bot.send_message(
            message.chat.id,
            f"✅ Отказ от заказа {order.code} зарегистрирован.\n\nПричина: {reason}",
            parse_mode='HTML'
        )
        
        logger.info(f"Заказ {order.code} отклонен клинером {telegram_user.user.full_name}. Причина: {reason}")
        
    except Exception as e:
        logger.error(f"Ошибка в process_decline_reason: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка")


def handle_order_start(bot, call, telegram_user):
    """Начало работы над заказом"""
    try:
        order_id = int(call.data.split('_')[-1])
        order = Order.objects.get(id=order_id)
        
        if not telegram_user.user or telegram_user.user != order.senior_cleaner:
            bot.answer_callback_query(call.id, "❌ У вас нет прав на это действие")
            return
        
        if order.status_senior_cleaner != 'ACCEPTED':
            bot.answer_callback_query(call.id, "❌ Сначала примите заказ")
            return
        
        if order.work_started_at:
            bot.answer_callback_query(call.id, "⚠️ Работа уже начата")
            return
        
        # Проверяем, нет ли другого заказа в работе
        active_order = Order.objects.filter(
            senior_cleaner=telegram_user.user,
            status_senior_cleaner='IN_PROGRESS'
        ).exclude(id=order_id).first()
        
        if active_order:
            bot.answer_callback_query(
                call.id,
                f"⚠️ У вас уже есть заказ в работе: {active_order.code}. Сначала завершите его.",
                show_alert=True
            )
            return
        
        # Начинаем работу
        order.status_senior_cleaner = 'IN_PROGRESS'
        order.work_started_at = timezone.now()
        order.save()
        
        # Обновляем статус клинера
        user = telegram_user.user
        user.is_available = False
        user.save()
        
        bot.answer_callback_query(call.id, "✅ Работа начата!")
        
        text = f"""
⏰ <b>Работа над заказом {order.code} НАЧАТА</b>

<b>Время начала:</b> {order.work_started_at.strftime('%d.%m.%Y %H:%M')}
<b>Клиент:</b> {get_client_full_name(order.client)}
<b>Адрес:</b> {order.address}

Не забудьте загрузить фото ДО начала работы!
"""
        
        markup = types.InlineKeyboardMarkup()
        btn_finish = types.InlineKeyboardButton('🏁 Завершить работу', callback_data=f'order_finish_{order.id}')
        btn_photo = types.InlineKeyboardButton('📷 Загрузить фото', callback_data=f'order_photo_{order.id}')
        markup.add(btn_finish)
        markup.add(btn_photo)
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='HTML'
        )
        
        logger.info(f"Работа над заказом {order.code} начата клинером {user.full_name}")
        
    except Order.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Заказ не найден")
    except Exception as e:
        logger.error(f"Ошибка в handle_order_start: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


def handle_order_finish(bot, call, telegram_user):
    """Завершение работы над заказом"""
    try:
        order_id = int(call.data.split('_')[-1])
        order = Order.objects.get(id=order_id)
        
        if not telegram_user.user or telegram_user.user != order.senior_cleaner:
            bot.answer_callback_query(call.id, "❌ У вас нет прав на это действие")
            return
        
        if order.status_senior_cleaner != 'IN_PROGRESS':
            bot.answer_callback_query(call.id, "❌ Работа не начата")
            return
        
        if order.work_finished_at:
            bot.answer_callback_query(call.id, "⚠️ Работа уже завершена")
            return
        
        # Завершаем работу
        order.status_senior_cleaner = 'PENDING_REVIEW'
        order.work_finished_at = timezone.now()
        order.save()
        
        # Обновляем статус клинера
        user = telegram_user.user
        user.is_available = True
        user.save()
        
        bot.answer_callback_query(call.id, "✅ Работа завершена!")
        
        # Вычисляем длительность
        duration = order.work_finished_at - order.work_started_at
        hours = duration.total_seconds() / 3600
        
        text = f"""
🏁 <b>Работа над заказом {order.code} ЗАВЕРШЕНА</b>

<b>Время начала:</b> {order.work_started_at.strftime('%d.%m.%Y %H:%M')}
<b>Время завершения:</b> {order.work_finished_at.strftime('%d.%m.%Y %H:%M')}
<b>Длительность:</b> {hours:.1f} ч

Заказ отправлен на проверку менеджеру.
Не забудьте загрузить фото ПОСЛЕ работы!
"""
        
        markup = types.InlineKeyboardMarkup()
        btn_photo = types.InlineKeyboardButton('📷 Загрузить фото', callback_data=f'order_photo_{order.id}')
        markup.add(btn_photo)
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
            parse_mode='HTML'
        )
        
        logger.info(f"Работа над заказом {order.code} завершена клинером {user.full_name}")
        
    except Order.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Заказ не найден")
    except Exception as e:
        logger.error(f"Ошибка в handle_order_finish: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


def handle_order_details(bot, call, telegram_user):
    """Показать подробную информацию о заказе"""
    try:
        order_id = int(call.data.split('_')[-1])
        order = Order.objects.get(id=order_id)
        
        from .cleaner_handlers import format_order_info, get_order_actions_keyboard
        
        text = format_order_info(order, detailed=True)
        
        is_senior = telegram_user.user and telegram_user.user.role == User.Role.SENIOR_CLEANER
        markup = get_order_actions_keyboard(order.id, is_senior)
        
        bot.answer_callback_query(call.id, "📄 Подробная информация")
        
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=markup,
            parse_mode='HTML'
        )
        
    except Order.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Заказ не найден")
    except Exception as e:
        logger.error(f"Ошибка в handle_order_details: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


def handle_order_photo(bot, call, telegram_user):
    """Запрос на загрузку фото"""
    try:
        order_id = int(call.data.split('_')[-1])
        order = Order.objects.get(id=order_id)
        
        bot.answer_callback_query(call.id, "📷 Отправьте фото")
        
        msg = bot.send_message(
            call.message.chat.id,
            f"""
📷 <b>Загрузка фото для заказа {order.code}</b>

Отправьте фото (можно несколько):
• Фото ДО начала работы
• Фото ПОСЛЕ завершения работы

Вы можете добавить описание к каждому фото.
""",
            parse_mode='HTML'
        )
        
        # Сохраняем контекст для обработки фото
        # В реальной системе лучше использовать состояния (FSM)
        
    except Order.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Заказ не найден")
    except Exception as e:
        logger.error(f"Ошибка в handle_order_photo: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


def handle_callback_query(bot, call):
    """Главный обработчик callback-запросов"""
    try:
        telegram_user = TelegramUser.objects.filter(id_user=call.from_user.id).first()
        
        if not telegram_user:
            bot.answer_callback_query(call.id, "❌ Пользователь не найден")
            return
        
        # Импортируем обработчики задач
        from . import task_handlers
        
        # Маршрутизация по типу callback
        if call.data.startswith('order_accept_'):
            handle_order_accept(bot, call, telegram_user)
        elif call.data.startswith('order_decline_'):
            handle_order_decline(bot, call, telegram_user)
        elif call.data.startswith('order_start_'):
            handle_order_start(bot, call, telegram_user)
        elif call.data.startswith('order_finish_'):
            handle_order_finish(bot, call, telegram_user)
        elif call.data.startswith('order_details_'):
            handle_order_details(bot, call, telegram_user)
        elif call.data.startswith('order_photo_'):
            handle_order_photo(bot, call, telegram_user)
        # Обработчики задач
        elif call.data.startswith('task_list_'):
            task_handlers.show_order_tasks(bot, call, telegram_user)
        elif call.data.startswith('task_add_'):
            task_handlers.handle_add_task(bot, call, telegram_user)
        elif call.data.startswith('task_assign_'):
            task_handlers.handle_assign_task(bot, call, telegram_user)
        elif call.data.startswith('task_manage_'):
            task_handlers.handle_manage_tasks(bot, call, telegram_user)
        elif call.data.startswith('task_edit_'):
            task_handlers.handle_edit_task(bot, call, telegram_user)
        elif call.data.startswith('task_done_'):
            task_handlers.handle_task_done(bot, call, telegram_user)
        elif call.data.startswith('task_undone_'):
            task_handlers.handle_task_undone(bot, call, telegram_user)
        elif call.data.startswith('task_delete_'):
            task_handlers.handle_task_delete(bot, call, telegram_user)
        else:
            bot.answer_callback_query(call.id, "❓ Неизвестная команда")
            
    except Exception as e:
        logger.error(f"Ошибка в handle_callback_query: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")
