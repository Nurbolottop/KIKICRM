import telebot
from django.conf import settings
from telebot import types
from .models import TelegramUser
from apps.users.models import User
import logging

logger = logging.getLogger(__name__)

# Инициализация бота
bot = telebot.TeleBot(settings.TELEGRAM_BOT_TOKEN, parse_mode='HTML')

# Импорт обработчиков для клинеров
from . import cleaner_handlers
from . import callback_handlers
from . import auth_handlers

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_handler(message):
    """Обработчик команды /start"""
    try:
        # Сохраняем или обновляем пользователя в базе данных
        telegram_user, created = TelegramUser.objects.get_or_create(
            id_user=message.from_user.id,
            defaults={
                'username': message.from_user.username,
                'first_name': message.from_user.first_name,
                'last_name': message.from_user.last_name,
                'chat_id': message.chat.id
            }
        )
        
        if not created:
            # Обновляем данные существующего пользователя
            telegram_user.username = message.from_user.username
            telegram_user.first_name = message.from_user.first_name
            telegram_user.last_name = message.from_user.last_name
            telegram_user.chat_id = message.chat.id
            telegram_user.save()
        
        # Проверяем авторизацию
        if auth_handlers.is_authenticated(telegram_user):
            user = telegram_user.user
            
            # Для клинеров показываем специальное меню
            if user.role in [User.Role.CLEANER, User.Role.SENIOR_CLEANER]:
                markup = cleaner_handlers.get_cleaner_keyboard()
                
                welcome_text = f"""
👋 <b>Добро пожаловать, {user.full_name}!</b>

Вы вошли как: <b>{user.get_role_display()}</b>

<b>Доступные функции:</b>
📋 Мои заказы - Активные заказы
🆕 Новые заказы - Назначенные заказы (для старших клинеров)
⏰ Текущий заказ - Заказ в работе
✅ Завершенные - История выполненных заказов
👤 Профиль - Ваши данные и статистика
📊 Статистика - Детальная статистика работы

Используйте кнопки меню для управления заказами.
"""
            else:
                # Для других ролей - обычное меню
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                btn1 = types.KeyboardButton('📊 Статистика')
                btn2 = types.KeyboardButton('📝 Заказы')
                btn3 = types.KeyboardButton('👤 Профиль')
                btn4 = types.KeyboardButton('ℹ️ Помощь')
                markup.add(btn1, btn2, btn3, btn4)
                
                welcome_text = f"""
👋 <b>Добро пожаловать, {user.full_name}!</b>

Вы вошли как: <b>{user.get_role_display()}</b>

<b>Доступные команды:</b>
/start - Главное меню
/help - Справка по командам
/stats - Статистика
/profile - Мой профиль

Используйте кнопки меню ниже для быстрого доступа к функциям.
"""
        else:
            # Пользователь не авторизован
            markup = auth_handlers.get_auth_keyboard()
            
            welcome_text = f"""
👋 <b>Добро пожаловать, {message.from_user.first_name}!</b>

🔐 <b>Вход в систему KIKI CRM</b>

Для работы с системой необходимо авторизоваться.

<b>Ваш Telegram ID:</b> <code>{message.from_user.id}</code>

Используйте кнопку '🔐 Войти в систему' и введите логин и пароль, которые вам выдал IT отдел.

<i>Если у вас нет учетных данных, обратитесь в IT отдел.</i>
"""
        
        bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=markup
        )
        
        logger.info(f"Пользователь {message.from_user.id} {'создан' if created else 'обновлен'}")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /start: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка. Попробуйте позже."
        )


# Обработчик команды /help
@bot.message_handler(commands=['help'])
def help_handler(message):
    """Обработчик команды /help"""
    try:
        help_text = """
ℹ️ <b>Справка по командам бота</b>

<b>Основные команды:</b>
/start - Перезапустить бота и показать главное меню
/help - Показать эту справку
/stats - Посмотреть статистику
/orders - Просмотр заказов
/profile - Информация о профиле

<b>Кнопки меню:</b>
📊 Статистика - Общая статистика по заказам
📝 Заказы - Список ваших заказов
👤 Профиль - Ваши данные
ℹ️ Помощь - Эта справка

<b>Дополнительная информация:</b>
Бот работает в режиме 24/7 и автоматически обрабатывает все сообщения.

По вопросам обращайтесь к администратору.
"""
        
        bot.send_message(message.chat.id, help_text)
        logger.info(f"Пользователь {message.from_user.id} запросил помощь")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /help: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка. Попробуйте позже."
        )


# Обработчик команды /stats
@bot.message_handler(commands=['stats'])
def stats_handler(message):
    """Обработчик команды /stats"""
    try:
        stats_text = """
📊 <b>Статистика</b>

📈 Всего пользователей: <code>Загрузка...</code>
📝 Активных заказов: <code>Загрузка...</code>
✅ Выполненных заказов: <code>Загрузка...</code>

<i>Функция в разработке. Скоро будет доступна полная статистика.</i>
"""
        
        bot.send_message(message.chat.id, stats_text)
        logger.info(f"Пользователь {message.from_user.id} запросил статистику")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /stats: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка. Попробуйте позже."
        )


# Обработчик команды /orders
@bot.message_handler(commands=['orders'])
def orders_handler(message):
    """Обработчик команды /orders"""
    try:
        orders_text = """
📝 <b>Мои заказы</b>

<i>У вас пока нет активных заказов.</i>

Для создания нового заказа обратитесь к менеджеру через веб-интерфейс CRM системы.
"""
        
        bot.send_message(message.chat.id, orders_text)
        logger.info(f"Пользователь {message.from_user.id} запросил заказы")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /orders: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка. Попробуйте позже."
        )


# Обработчик команды /logout
@bot.message_handler(commands=['logout'])
def logout_command_handler(message):
    """Обработчик команды /logout"""
    try:
        telegram_user = TelegramUser.objects.filter(id_user=message.from_user.id).first()
        auth_handlers.handle_logout(bot, message, telegram_user)
    except Exception as e:
        logger.error(f"Ошибка в обработчике /logout: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка.")


# Обработчик команды /profile
@bot.message_handler(commands=['profile'])
def profile_handler(message):
    """Обработчик команды /profile"""
    try:
        user = TelegramUser.objects.filter(id_user=message.from_user.id).first()
        
        if user:
            profile_text = f"""
👤 <b>Мой профиль</b>

<b>Имя:</b> {user.first_name or 'Не указано'}
<b>Фамилия:</b> {user.last_name or 'Не указано'}
<b>Username:</b> @{user.username or 'Не указано'}
<b>ID:</b> <code>{user.id_user}</code>
<b>Дата регистрации:</b> {user.created.strftime('%d.%m.%Y %H:%M')}
"""
        else:
            profile_text = """
👤 <b>Мой профиль</b>

<i>Профиль не найден. Используйте команду /start для регистрации.</i>
"""
        
        bot.send_message(message.chat.id, profile_text)
        logger.info(f"Пользователь {message.from_user.id} запросил профиль")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике /profile: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка. Попробуйте позже."
        )


# Обработчик текстовых сообщений с кнопок
@bot.message_handler(func=lambda message: message.text in [
    '📊 Статистика', '📝 Заказы', '👤 Профиль', 'ℹ️ Помощь',
    '📋 Мои заказы', '🆕 Новые заказы', '⏰ Текущий заказ', '✅ Завершенные',
    '🔐 Войти в систему', '🚪 Выйти'
])
def button_handler(message):
    """Обработчик нажатий на кнопки меню"""
    try:
        telegram_user = TelegramUser.objects.filter(id_user=message.from_user.id).first()
        
        if not telegram_user:
            bot.send_message(message.chat.id, "❌ Пользователь не найден. Используйте /start")
            return
        
        # Обработчики авторизации
        if message.text == '🔐 Войти в систему':
            auth_handlers.handle_login_request(bot, message, telegram_user)
            return
        elif message.text == '🚪 Выйти':
            auth_handlers.handle_logout(bot, message, telegram_user)
            return
        
        # Проверка авторизации для остальных функций
        if not auth_handlers.is_authenticated(telegram_user):
            bot.send_message(
                message.chat.id,
                "❌ Для доступа к этой функции необходимо авторизоваться.\n\nИспользуйте кнопку '🔐 Войти в систему'",
                reply_markup=auth_handlers.get_auth_keyboard()
            )
            return
        
        # Обработчики для клинеров
        if message.text == '📋 Мои заказы':
            cleaner_handlers.handle_my_orders(bot, message, telegram_user)
        elif message.text == '🆕 Новые заказы':
            cleaner_handlers.handle_new_orders(bot, message, telegram_user)
        elif message.text == '⏰ Текущий заказ':
            cleaner_handlers.handle_current_order(bot, message, telegram_user)
        elif message.text == '✅ Завершенные':
            cleaner_handlers.handle_completed_orders(bot, message, telegram_user)
        # Общие обработчики
        elif message.text == '📊 Статистика':
            if telegram_user.user and telegram_user.user.role in [User.Role.CLEANER, User.Role.SENIOR_CLEANER]:
                cleaner_handlers.handle_cleaner_stats(bot, message, telegram_user)
            else:
                stats_handler(message)
        elif message.text == '📝 Заказы':
            if telegram_user.user and telegram_user.user.role in [User.Role.CLEANER, User.Role.SENIOR_CLEANER]:
                cleaner_handlers.handle_my_orders(bot, message, telegram_user)
            else:
                orders_handler(message)
        elif message.text == '👤 Профиль':
            if telegram_user.user and telegram_user.user.role in [User.Role.CLEANER, User.Role.SENIOR_CLEANER]:
                cleaner_handlers.handle_cleaner_profile(bot, message, telegram_user)
            else:
                profile_handler(message)
        elif message.text == 'ℹ️ Помощь':
            help_handler(message)
            
    except Exception as e:
        logger.error(f"Ошибка в обработчике кнопок: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка. Попробуйте позже."
        )


# Обработчик всех остальных текстовых сообщений
@bot.message_handler(content_types=['text'])
def text_handler(message):
    """Обработчик всех текстовых сообщений"""
    try:
        response_text = f"""
💬 <b>Получено сообщение:</b> "{message.text}"

Я обработал ваше сообщение. Для просмотра доступных команд используйте /help

<i>Автоматические ответы на сообщения будут добавлены в следующих версиях.</i>
"""
        
        bot.send_message(message.chat.id, response_text)
        logger.info(f"Пользователь {message.from_user.id} отправил сообщение: {message.text}")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике текста: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка. Попробуйте позже."
        )


# Обработчик фото
@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    """Обработчик фотографий"""
    try:
        bot.send_message(
            message.chat.id,
            "📷 Фото получено! Функция обработки фотографий будет добавлена позже."
        )
        logger.info(f"Пользователь {message.from_user.id} отправил фото")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике фото: {e}")


# Обработчик документов
@bot.message_handler(content_types=['document'])
def document_handler(message):
    """Обработчик документов"""
    try:
        bot.send_message(
            message.chat.id,
            "📄 Документ получен! Функция обработки документов будет добавлена позже."
        )
        logger.info(f"Пользователь {message.from_user.id} отправил документ")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике документов: {e}")


# Обработчик голосовых сообщений
@bot.message_handler(content_types=['voice'])
def voice_handler(message):
    """Обработчик голосовых сообщений"""
    try:
        bot.send_message(
            message.chat.id,
            "🎤 Голосовое сообщение получено! Функция обработки голоса будет добавлена позже."
        )
        logger.info(f"Пользователь {message.from_user.id} отправил голосовое сообщение")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике голоса: {e}")


# Обработчик стикеров
@bot.message_handler(content_types=['sticker'])
def sticker_handler(message):
    """Обработчик стикеров"""
    try:
        bot.send_message(
            message.chat.id,
            "😊 Стикер получен!"
        )
        logger.info(f"Пользователь {message.from_user.id} отправил стикер")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике стикеров: {e}")


# Обработчик видео
@bot.message_handler(content_types=['video'])
def video_handler(message):
    """Обработчик видео"""
    try:
        bot.send_message(
            message.chat.id,
            "🎥 Видео получено! Функция обработки видео будет добавлена позже."
        )
        logger.info(f"Пользователь {message.from_user.id} отправил видео")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике видео: {e}")


# Обработчик локации
@bot.message_handler(content_types=['location'])
def location_handler(message):
    """Обработчик геолокации"""
    try:
        bot.send_message(
            message.chat.id,
            f"📍 Локация получена!\nШирота: {message.location.latitude}\nДолгота: {message.location.longitude}"
        )
        logger.info(f"Пользователь {message.from_user.id} отправил локацию")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике локации: {e}")


# Обработчик контактов
@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    """Обработчик контактов"""
    try:
        bot.send_message(
            message.chat.id,
            "📞 Контакт получен! Спасибо за предоставленную информацию."
        )
        logger.info(f"Пользователь {message.from_user.id} отправил контакт")
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике контактов: {e}")


# Обработчик callback-кнопок
@bot.callback_query_handler(func=lambda call: True)
def callback_query_handler(call):
    """Обработчик всех callback-запросов"""
    callback_handlers.handle_callback_query(bot, call)


logger.info("Telegram бот инициализирован успешно")
