"""
Client Telegram Bot Service.
Обработка сообщений от клиентов через Telegram.
"""
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from django.conf import settings
from apps.orders.models import Order, OrderStatus

logger = logging.getLogger(__name__)


# Human-readable статусы заказов
ORDER_STATUS_LABELS = {
    'NEW': 'Новый',
    'CONFIRMED': 'Подтвержден',
    'ASSIGNED': 'Назначен',
    'IN_PROGRESS': 'В работе',
    'COMPLETED': 'Завершен',
    'CANCELLED': 'Отменен',
}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start."""
    welcome_message = (
        "Здравствуйте! 👋\n\n"
        "Отправьте код вашего заказа, например:\n"
        "<code>KIKI-0001</code>\n\n"
        "Я покажу информацию о вашем заказе."
    )
    await update.message.reply_html(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help."""
    help_message = (
        "🔍 <b>Как проверить заказ:</b>\n\n"
        "1. Отправьте код заказа (например: KIKI-0001)\n"
        "2. Бот покажет актуальный статус\n\n"
        "Код заказа можно найти в SMS или email уведомлении."
    )
    await update.message.reply_html(help_message)


def normalize_order_code(code: str) -> str:
    """
    Нормализация кода заказа:
    - trim пробелов
    - upper() для единообразия
    """
    return code.strip().upper()


def format_order_response(order: Order) -> str:
    """
    Форматирование ответа с информацией о заказе.
    Безопасное отображение — без чувствительных данных.
    """
    status_label = ORDER_STATUS_LABELS.get(order.status, order.status)
    
    response = (
        f"📦 <b>Заказ:</b> {order.order_code}\n"
        f"👤 <b>Клиент:</b> {order.client.name}\n"
        f"🧽 <b>Услуга:</b> {order.service.name}\n"
        f"📍 <b>Адрес:</b> {order.address}\n"
        f"📅 <b>Дата:</b> {order.scheduled_date.strftime('%d.%m.%Y')}\n"
        f"🕒 <b>Время:</b> {order.scheduled_time.strftime('%H:%M') if order.scheduled_time else '—'}\n"
        f"📌 <b>Статус:</b> {status_label}"
    )
    
    return response


def format_not_found_response(order_code: str) -> str:
    """Форматирование ответа при не найденном заказе."""
    return (
        f"❌ Заказ с кодом <code>{order_code}</code> не найден.\n\n"
        "Проверьте код и попробуйте снова.\n"
        "Пример правильного формата: <code>KIKI-0001</code>"
    )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений (поиск заказа)."""
    text = update.message.text
    
    # Нормализация кода заказа
    order_code = normalize_order_code(text)
    
    # Проверка формата кода (должен содержать KIKI-)
    if not order_code.startswith('KIKI-'):
        await update.message.reply_html(
            "⚠️ Неверный формат кода.\n\n"
            "Отправьте код в формате: <code>KIKI-0001</code>"
        )
        return
    
    try:
        # Поиск заказа
        order = Order.objects.select_related('client', 'service').get(
            order_code=order_code
        )
        
        # Формирование ответа
        response = format_order_response(order)
        await update.message.reply_html(response)
        
    except Order.DoesNotExist:
        response = format_not_found_response(order_code)
        await update.message.reply_html(response)
        
    except Exception as e:
        logger.error(f"Error looking up order {order_code}: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка при поиске заказа.\n"
            "Попробуйте позже или обратитесь в поддержку."
        )


class ClientBotService:
    """Сервис для управления клиентским Telegram ботом."""
    
    def __init__(self, token: str = None):
        self.token = token
        self.application = None
    
    def setup(self, token: str = None):
        """Настройка бота с токеном."""
        if token:
            self.token = token
        
        if not self.token:
            raise ValueError("Bot token is required")
        
        # Создание приложения
        self.application = Application.builder().token(self.token).build()
        
        # Регистрация обработчиков
        self.application.add_handler(CommandHandler("start", start_command))
        self.application.add_handler(CommandHandler("help", help_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        logger.info("Client bot handlers registered successfully")
        
        return self
    
    def run(self):
        """Запуск бота в polling режиме."""
        if not self.application:
            raise RuntimeError("Bot not set up. Call setup() first.")
        
        logger.info("Starting client bot polling...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    async def start_async(self):
        """Асинхронный запуск бота (для webhook режима)."""
        if not self.application:
            raise RuntimeError("Bot not set up. Call setup() first.")
        
        await self.application.initialize()
        await self.application.start()
        logger.info("Client bot started successfully")
    
    async def stop_async(self):
        """Остановка бота."""
        if self.application:
            await self.application.stop()
            logger.info("Client bot stopped")


def get_client_bot_service():
    """
    Фабричная функция для создания сервиса бота с токеном из настроек.
    """
    from apps.telegram_bot.models import ClientBotSettings
    
    try:
        settings_obj = ClientBotSettings.objects.filter(is_active=True).first()
        if settings_obj and settings_obj.bot_token:
            return ClientBotService().setup(settings_obj.bot_token)
    except Exception as e:
        logger.error(f"Failed to load client bot settings: {e}")
    
    return None
