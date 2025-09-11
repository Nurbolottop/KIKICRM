from django.core.management.base import BaseCommand
from apps.telegram_bot.views import bot
import time
import sys
import logging
from telebot.apihelper import ApiException

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Запуск Telegram бота с автоматическим переподключением'

    def handle(self, *args, **kwargs):
        while True:
            try:
                logger.info("Бот запущен и начал прослушивание...")
                print("Бот запущен и начал прослушивание...")
                # Запускаем бота с параметрами для непрерывной работы
                bot.polling(none_stop=True, interval=3)
            except ApiException as e:
                logger.error(f"Ошибка API Telegram: {e}")
                time.sleep(15)
            except Exception as e:
                logger.error(f"Непредвиденная ошибка: {e}")
                time.sleep(15)
            finally:
                try:
                    bot.stop_polling()
                except Exception as e:
                    logger.error(f"Ошибка при остановке бота: {e}")
                logger.info("Перезапуск бота через 15 секунд...")
                time.sleep(15)