import telebot
from django.conf import settings
from telebot import types
from apps.telegram_bot.models import TelegramUser
from apps.users.models import User
import logging

logger = logging.getLogger(__name__)

# Инициализация бота
bot = telebot.TeleBot(settings.TELEGRAM_BOT_TOKEN, parse_mode='HTML')


logger.info("Telegram бот инициализирован успешно")