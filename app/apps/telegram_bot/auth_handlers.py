"""
Обработчики авторизации для Telegram бота
Клинеры входят через логин/пароль из системы
"""
from django.contrib.auth import authenticate
from telebot import types
from .models import TelegramUser
from apps.users.models import User
import logging

logger = logging.getLogger(__name__)


def get_auth_keyboard():
    """Клавиатура для неавторизованного пользователя"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_login = types.KeyboardButton('🔐 Войти в систему')
    btn_help = types.KeyboardButton('ℹ️ Помощь')
    markup.add(btn_login, btn_help)
    return markup


def is_authenticated(telegram_user):
    """Проверка авторизации пользователя"""
    if not telegram_user:
        return False
    
    if not telegram_user.user:
        return False
    
    if not telegram_user.is_active:
        return False
    
    return True


def require_auth(func):
    """Декоратор для проверки авторизации"""
    def wrapper(bot, message, telegram_user=None, *args, **kwargs):
        if telegram_user is None:
            telegram_user = TelegramUser.objects.filter(id_user=message.from_user.id).first()
        
        if not is_authenticated(telegram_user):
            bot.send_message(
                message.chat.id,
                "❌ Для доступа к этой функции необходимо авторизоваться.\n\nИспользуйте кнопку '🔐 Войти в систему'",
                reply_markup=get_auth_keyboard()
            )
            return
        
        return func(bot, message, telegram_user, *args, **kwargs)
    
    return wrapper


def handle_login_request(bot, message, telegram_user):
    """Запрос на авторизацию"""
    try:
        # Если уже авторизован
        if is_authenticated(telegram_user):
            user = telegram_user.user
            bot.send_message(
                message.chat.id,
                f"✅ Вы уже авторизованы как <b>{user.full_name}</b> ({user.get_role_display()})",
                parse_mode='HTML'
            )
            return
        
        # Запрашиваем логин
        msg = bot.send_message(
            message.chat.id,
            """
🔐 <b>Вход в систему KIKI CRM</b>

Введите ваш <b>логин</b> (username):

<i>Логин и пароль выдаются IT отделом при приеме на работу.</i>
""",
            parse_mode='HTML'
        )
        
        bot.register_next_step_handler(msg, lambda m: process_login(bot, m, telegram_user))
        
    except Exception as e:
        logger.error(f"Ошибка в handle_login_request: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Попробуйте позже.")


def process_login(bot, message, telegram_user):
    """Обработка ввода логина"""
    try:
        username = message.text.strip()
        
        # Проверяем, что логин не пустой
        if not username:
            bot.send_message(
                message.chat.id,
                "❌ Логин не может быть пустым. Попробуйте снова: /start"
            )
            return
        
        # ПРОВЕРЯЕМ СУЩЕСТВОВАНИЕ ПОЛЬЗОВАТЕЛЯ СРАЗУ
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            bot.send_message(
                message.chat.id,
                f"""
❌ <b>Пользователь не найден</b>

Логин <code>{username}</code> не существует в системе.

Проверьте правильность написания логина или обратитесь в IT отдел.

Для новой попытки используйте кнопку '🔐 Войти в систему'
""",
                parse_mode='HTML',
                reply_markup=get_auth_keyboard()
            )
            logger.warning(f"Попытка входа с несуществующим логином: {username} от Telegram ID: {message.from_user.id}")
            return
        
        # Проверяем роль пользователя
        if user.role not in [User.Role.CLEANER, User.Role.SENIOR_CLEANER]:
            bot.send_message(
                message.chat.id,
                f"""
❌ <b>Доступ запрещен</b>

Пользователь: <b>{user.full_name}</b>
Роль: <b>{user.get_role_display()}</b>

Telegram бот доступен только для клинеров.
Для работы используйте веб-интерфейс CRM системы.
""",
                parse_mode='HTML',
                reply_markup=get_auth_keyboard()
            )
            logger.warning(f"Попытка входа пользователя с ролью {user.role}: {username}")
            return
        
        # Проверяем статус пользователя
        if user.status == User.Status.FIRED:
            bot.send_message(
                message.chat.id,
                f"""
❌ <b>Доступ запрещен</b>

Пользователь: <b>{user.full_name}</b>
Статус: <b>Уволен</b>

Ваш аккаунт деактивирован.
Обратитесь в отдел кадров для уточнения информации.
""",
                parse_mode='HTML',
                reply_markup=get_auth_keyboard()
            )
            logger.warning(f"Попытка входа уволенного сотрудника: {username}")
            return
        
        # Сохраняем логин и user_id временно
        if not hasattr(bot, 'temp_auth_data'):
            bot.temp_auth_data = {}
        
        bot.temp_auth_data[message.from_user.id] = {
            'username': username,
            'user_id': user.id,
            'full_name': user.full_name
        }
        
        # Запрашиваем пароль
        msg = bot.send_message(
            message.chat.id,
            f"""
🔐 <b>Вход в систему</b>

✅ Пользователь найден: <b>{user.full_name}</b>
Роль: <b>{user.get_role_display()}</b>

Теперь введите ваш <b>пароль</b>:

<i>⚠️ Пароль будет автоматически удален из чата после проверки.</i>
""",
            parse_mode='HTML'
        )
        
        bot.register_next_step_handler(msg, lambda m: process_password(bot, m, telegram_user))
        
    except Exception as e:
        logger.error(f"Ошибка в process_login: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка. Попробуйте снова: /start")


def process_password(bot, message, telegram_user):
    """Обработка ввода пароля и авторизация"""
    try:
        password = message.text.strip()
        
        # Удаляем сообщение с паролем из чата
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        
        # Получаем логин из временного хранилища
        if not hasattr(bot, 'temp_auth_data') or message.from_user.id not in bot.temp_auth_data:
            bot.send_message(
                message.chat.id,
                "❌ Сессия авторизации истекла. Начните заново: /start"
            )
            return
        
        username = bot.temp_auth_data[message.from_user.id]['username']
        
        # Очищаем временные данные
        del bot.temp_auth_data[message.from_user.id]
        
        # Проверяем, что пароль не пустой
        if not password:
            bot.send_message(
                message.chat.id,
                "❌ Пароль не может быть пустым. Попробуйте снова: /start"
            )
            return
        
        # Аутентификация через Django
        user = authenticate(username=username, password=password)
        
        if user is None:
            # Неверный пароль (логин уже проверен)
            full_name = bot.temp_auth_data[message.from_user.id].get('full_name', username)
            bot.send_message(
                message.chat.id,
                f"""
❌ <b>Неверный пароль</b>

Пользователь: <b>{full_name}</b>
Логин: <code>{username}</code>

Пароль введен неправильно.

Если вы забыли пароль, обратитесь в IT отдел.

Для новой попытки используйте кнопку '🔐 Войти в систему'
""",
                parse_mode='HTML',
                reply_markup=get_auth_keyboard()
            )
            logger.warning(f"Неверный пароль для username: {username} от Telegram ID: {message.from_user.id}")
            return
        
        # Привязываем Telegram аккаунт к пользователю системы
        telegram_user.user = user
        telegram_user.is_active = True
        telegram_user.save()
        
        # Обновляем telegram_id в профиле пользователя
        if not user.telegram_id:
            user.telegram_id = message.from_user.id
            user.save()
        
        # Импортируем функцию для получения клавиатуры клинера
        from .cleaner_handlers import get_cleaner_keyboard
        
        # Успешная авторизация
        bot.send_message(
            message.chat.id,
            f"""
✅ <b>Вход выполнен успешно!</b>

<b>ФИО:</b> {user.full_name}
<b>Роль:</b> {user.get_role_display()}
<b>Статус:</b> {user.get_status_display()}

Теперь вы можете управлять своими заказами через бота.
Используйте кнопки меню ниже.
""",
            parse_mode='HTML',
            reply_markup=get_cleaner_keyboard()
        )
        
        logger.info(f"Успешная авторизация: {user.full_name} ({user.username}) - Telegram ID: {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка в process_password: {e}")
        bot.send_message(
            message.chat.id,
            "❌ Произошла ошибка при авторизации. Попробуйте позже."
        )


def handle_logout(bot, message, telegram_user):
    """Выход из аккаунта"""
    try:
        if not is_authenticated(telegram_user):
            bot.send_message(
                message.chat.id,
                "ℹ️ Вы не авторизованы.",
                reply_markup=get_auth_keyboard()
            )
            return
        
        user_name = telegram_user.user.full_name
        
        # Отвязываем пользователя
        telegram_user.user = None
        telegram_user.is_active = False
        telegram_user.save()
        
        bot.send_message(
            message.chat.id,
            f"""
👋 <b>Выход выполнен</b>

{user_name}, вы вышли из системы.

Для повторного входа используйте кнопку '🔐 Войти в систему'
""",
            parse_mode='HTML',
            reply_markup=get_auth_keyboard()
        )
        
        logger.info(f"Выход из системы: {user_name} - Telegram ID: {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_logout: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка.")


def check_session(telegram_user):
    """Проверка активности сессии"""
    if not telegram_user:
        return False
    
    if not telegram_user.user:
        return False
    
    # Проверяем, не был ли пользователь уволен
    if telegram_user.user.status == User.Status.FIRED:
        telegram_user.user = None
        telegram_user.is_active = False
        telegram_user.save()
        return False
    
    return telegram_user.is_active
