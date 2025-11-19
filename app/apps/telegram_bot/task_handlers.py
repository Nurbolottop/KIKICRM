"""
Обработчики для управления задачами по заказу
"""
from telebot import types
from apps.orders.models import Order, Task
from apps.users.models import User
from .models import TelegramUser
from .cleaner_handlers import get_client_full_name
import logging

logger = logging.getLogger(__name__)


def show_order_tasks(bot, call, telegram_user):
    """Показать задачи по заказу"""
    try:
        order_id = int(call.data.split('_')[-1])
        order = Order.objects.get(id=order_id)
        
        if not telegram_user.user or telegram_user.user != order.senior_cleaner:
            bot.answer_callback_query(call.id, "❌ У вас нет прав на это действие")
            return
        
        tasks = order.tasks.all()
        
        if not tasks.exists():
            text = f"""
📋 <b>Задачи по заказу {order.code}</b>

<b>Клиент:</b> {get_client_full_name(order.client)}
<b>Адрес:</b> {order.address}

❌ Задачи не созданы

Создайте задачи для распределения работы между клинерами.
"""
            markup = types.InlineKeyboardMarkup()
            btn_add = types.InlineKeyboardButton('➕ Добавить задачу', callback_data=f'task_add_{order.id}')
            btn_back = types.InlineKeyboardButton('◀️ Назад', callback_data=f'order_details_{order.id}')
            markup.add(btn_add)
            markup.add(btn_back)
        else:
            text = f"""
📋 <b>Задачи по заказу {order.code}</b>

<b>Клиент:</b> {get_client_full_name(order.client)}
<b>Адрес:</b> {order.address}

<b>Всего задач:</b> {tasks.count()}
"""
            
            # Статистика по задачам
            done_count = tasks.filter(status='DONE').count()
            in_progress_count = tasks.filter(status='IN_PROGRESS').count()
            
            text += f"""
✅ Выполнено: {done_count}
⏳ В работе: {in_progress_count}

<b>Список задач:</b>
"""
            
            for i, task in enumerate(tasks, 1):
                status_emoji = '✅' if task.status == 'DONE' else '⏳'
                cleaner_name = task.cleaner.full_name if task.cleaner else 'Не назначен'
                text += f"\n{i}. {status_emoji} {task.description}"
                text += f"\n   👤 {cleaner_name}"
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            btn_add = types.InlineKeyboardButton('➕ Добавить', callback_data=f'task_add_{order.id}')
            btn_manage = types.InlineKeyboardButton('⚙️ Управление', callback_data=f'task_manage_{order.id}')
            btn_back = types.InlineKeyboardButton('◀️ Назад', callback_data=f'order_details_{order.id}')
            markup.add(btn_add, btn_manage)
            markup.add(btn_back)
        
        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=markup,
            parse_mode='HTML'
        )
        
    except Order.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Заказ не найден")
    except Exception as e:
        logger.error(f"Ошибка в show_order_tasks: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


def handle_add_task(bot, call, telegram_user):
    """Начать процесс добавления задачи"""
    try:
        order_id = int(call.data.split('_')[-1])
        order = Order.objects.get(id=order_id)
        
        if not telegram_user.user or telegram_user.user != order.senior_cleaner:
            bot.answer_callback_query(call.id, "❌ У вас нет прав на это действие")
            return
        
        bot.answer_callback_query(call.id)
        
        msg = bot.send_message(
            call.message.chat.id,
            f"""
➕ <b>Добавление задачи к заказу {order.code}</b>

Введите описание задачи:

<i>Например: "Помыть окна", "Очистить холодильник", "Убрать балкон"</i>
""",
            parse_mode='HTML'
        )
        
        # Сохраняем контекст
        bot.register_next_step_handler(msg, lambda m: process_task_description(bot, m, order, telegram_user))
        
    except Order.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Заказ не найден")
    except Exception as e:
        logger.error(f"Ошибка в handle_add_task: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


def process_task_description(bot, message, order, telegram_user):
    """Обработка описания задачи"""
    try:
        description = message.text.strip()
        
        if not description:
            bot.send_message(message.chat.id, "❌ Описание не может быть пустым")
            return
        
        # Получаем список клинеров для назначения
        cleaners = list(order.cleaners.all())
        if order.senior_cleaner:
            cleaners.insert(0, order.senior_cleaner)
        
        if not cleaners:
            # Создаем задачу без исполнителя
            task = Task.objects.create(
                order=order,
                description=description,
                status='IN_PROGRESS'
            )
            
            bot.send_message(
                message.chat.id,
                f"""
✅ <b>Задача создана!</b>

📝 {description}
👤 Исполнитель: Не назначен

Добавьте клинеров к заказу чтобы назначать им задачи.
""",
                parse_mode='HTML'
            )
            return
        
        # Показываем кнопки для выбора исполнителя
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        # Кнопка "Назначить себе" в самом верху
        btn_myself = types.InlineKeyboardButton(
            f"👤 Назначить себе ({telegram_user.user.full_name})",
            callback_data=f'task_assign_{order.id}_{telegram_user.user.id}_{description[:50]}'
        )
        markup.add(btn_myself)
        
        # Остальные клинеры
        for cleaner in cleaners:
            if cleaner.id != telegram_user.user.id:  # Не дублируем себя
                btn = types.InlineKeyboardButton(
                    f"👤 {cleaner.full_name}",
                    callback_data=f'task_assign_{order.id}_{cleaner.id}_{description[:50]}'
                )
                markup.add(btn)
        
        # Кнопка без исполнителя
        btn_none = types.InlineKeyboardButton(
            "❌ Без исполнителя",
            callback_data=f'task_assign_{order.id}_0_{description[:50]}'
        )
        markup.add(btn_none)
        
        # Сохраняем полное описание во временном хранилище
        if not hasattr(bot, 'temp_task_data'):
            bot.temp_task_data = {}
        bot.temp_task_data[message.from_user.id] = description
        
        bot.send_message(
            message.chat.id,
            f"""
➕ <b>Новая задача</b>

📝 {description}

Выберите исполнителя:
""",
            reply_markup=markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка в process_task_description: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка")


def handle_assign_task(bot, call, telegram_user):
    """Назначение исполнителя на задачу"""
    try:
        parts = call.data.split('_')
        order_id = int(parts[2])
        cleaner_id = int(parts[3])
        
        order = Order.objects.get(id=order_id)
        
        if not telegram_user.user or telegram_user.user != order.senior_cleaner:
            bot.answer_callback_query(call.id, "❌ У вас нет прав на это действие")
            return
        
        # Получаем полное описание из временного хранилища
        description = bot.temp_task_data.get(call.from_user.id, '_'.join(parts[4:]))
        
        # Создаем задачу
        cleaner = User.objects.get(id=cleaner_id) if cleaner_id > 0 else None
        
        task = Task.objects.create(
            order=order,
            cleaner=cleaner,
            description=description,
            status='IN_PROGRESS'
        )
        
        # Очищаем временные данные
        if hasattr(bot, 'temp_task_data') and call.from_user.id in bot.temp_task_data:
            del bot.temp_task_data[call.from_user.id]
        
        bot.answer_callback_query(call.id, "✅ Задача создана!")
        
        cleaner_name = cleaner.full_name if cleaner else "Не назначен"
        
        bot.edit_message_text(
            f"""
✅ <b>Задача создана!</b>

📝 {description}
👤 Исполнитель: {cleaner_name}
📋 Заказ: {order.code}

Задача добавлена к заказу.
""",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )
        
        logger.info(f"Задача создана: {description} для {cleaner_name} по заказу {order.code}")
        
    except Order.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Заказ не найден")
    except User.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Клинер не найден")
    except Exception as e:
        logger.error(f"Ошибка в handle_assign_task: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


def handle_manage_tasks(bot, call, telegram_user):
    """Управление задачами (изменение статуса, переназначение)"""
    try:
        order_id = int(call.data.split('_')[-1])
        order = Order.objects.get(id=order_id)
        
        if not telegram_user.user or telegram_user.user != order.senior_cleaner:
            bot.answer_callback_query(call.id, "❌ У вас нет прав на это действие")
            return
        
        tasks = order.tasks.all()
        
        if not tasks.exists():
            bot.answer_callback_query(call.id, "❌ Нет задач для управления")
            return
        
        bot.answer_callback_query(call.id)
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for task in tasks:
            status_emoji = '✅' if task.status == 'DONE' else '⏳'
            cleaner_name = task.cleaner.full_name if task.cleaner else 'Не назначен'
            
            btn_text = f"{status_emoji} {task.description[:30]} | {cleaner_name}"
            btn = types.InlineKeyboardButton(
                btn_text,
                callback_data=f'task_edit_{task.id}'
            )
            markup.add(btn)
        
        btn_back = types.InlineKeyboardButton('◀️ Назад', callback_data=f'task_list_{order.id}')
        markup.add(btn_back)
        
        bot.send_message(
            call.message.chat.id,
            f"""
⚙️ <b>Управление задачами</b>

Заказ: {order.code}

Выберите задачу для редактирования:
""",
            reply_markup=markup,
            parse_mode='HTML'
        )
        
    except Order.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Заказ не найден")
    except Exception as e:
        logger.error(f"Ошибка в handle_manage_tasks: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


def handle_edit_task(bot, call, telegram_user):
    """Редактирование задачи"""
    try:
        task_id = int(call.data.split('_')[-1])
        task = Task.objects.get(id=task_id)
        order = task.order
        
        if not telegram_user.user or telegram_user.user != order.senior_cleaner:
            bot.answer_callback_query(call.id, "❌ У вас нет прав на это действие")
            return
        
        bot.answer_callback_query(call.id)
        
        status_text = "✅ Выполнено" if task.status == 'DONE' else "⏳ В работе"
        cleaner_name = task.cleaner.full_name if task.cleaner else "Не назначен"
        
        text = f"""
📝 <b>Редактирование задачи</b>

<b>Описание:</b> {task.description}
<b>Статус:</b> {status_text}
<b>Исполнитель:</b> {cleaner_name}
<b>Заказ:</b> {order.code}
"""
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Кнопка изменения статуса
        if task.status == 'IN_PROGRESS':
            btn_status = types.InlineKeyboardButton('✅ Отметить выполненной', callback_data=f'task_done_{task.id}')
        else:
            btn_status = types.InlineKeyboardButton('⏳ Вернуть в работу', callback_data=f'task_undone_{task.id}')
        
        btn_reassign = types.InlineKeyboardButton('👤 Переназначить', callback_data=f'task_reassign_{task.id}')
        btn_delete = types.InlineKeyboardButton('🗑 Удалить', callback_data=f'task_delete_{task.id}')
        btn_back = types.InlineKeyboardButton('◀️ Назад', callback_data=f'task_manage_{order.id}')
        
        markup.add(btn_status)
        markup.add(btn_reassign)
        markup.add(btn_delete)
        markup.add(btn_back)
        
        bot.send_message(
            call.message.chat.id,
            text,
            reply_markup=markup,
            parse_mode='HTML'
        )
        
    except Task.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Задача не найдена")
    except Exception as e:
        logger.error(f"Ошибка в handle_edit_task: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


def handle_task_done(bot, call, telegram_user):
    """Отметить задачу выполненной"""
    try:
        task_id = int(call.data.split('_')[-1])
        task = Task.objects.get(id=task_id)
        
        task.status = 'DONE'
        task.save()
        
        bot.answer_callback_query(call.id, "✅ Задача отмечена выполненной")
        
        bot.edit_message_text(
            f"""
✅ <b>Задача выполнена!</b>

📝 {task.description}
👤 {task.cleaner.full_name if task.cleaner else 'Не назначен'}
""",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )
        
    except Task.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Задача не найдена")
    except Exception as e:
        logger.error(f"Ошибка в handle_task_done: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


def handle_task_undone(bot, call, telegram_user):
    """Вернуть задачу в работу"""
    try:
        task_id = int(call.data.split('_')[-1])
        task = Task.objects.get(id=task_id)
        
        task.status = 'IN_PROGRESS'
        task.save()
        
        bot.answer_callback_query(call.id, "⏳ Задача возвращена в работу")
        
        bot.edit_message_text(
            f"""
⏳ <b>Задача в работе</b>

📝 {task.description}
👤 {task.cleaner.full_name if task.cleaner else 'Не назначен'}
""",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )
        
    except Task.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Задача не найдена")
    except Exception as e:
        logger.error(f"Ошибка в handle_task_undone: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")


def handle_task_delete(bot, call, telegram_user):
    """Удалить задачу"""
    try:
        task_id = int(call.data.split('_')[-1])
        task = Task.objects.get(id=task_id)
        order = task.order
        
        if not telegram_user.user or telegram_user.user != order.senior_cleaner:
            bot.answer_callback_query(call.id, "❌ У вас нет прав на это действие")
            return
        
        description = task.description
        task.delete()
        
        bot.answer_callback_query(call.id, "🗑 Задача удалена")
        
        bot.edit_message_text(
            f"""
🗑 <b>Задача удалена</b>

📝 {description}
""",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML'
        )
        
    except Task.DoesNotExist:
        bot.answer_callback_query(call.id, "❌ Задача не найдена")
    except Exception as e:
        logger.error(f"Ошибка в handle_task_delete: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка")
