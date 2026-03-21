"""
Management command to run the client Telegram bot.
"""
from django.core.management.base import BaseCommand
from apps.telegram_bot.services.client_bot_service import get_client_bot_service


class Command(BaseCommand):
    help = 'Run the client Telegram bot for order lookup'

    def handle(self, *args, **options):
        self.stdout.write('Starting client bot...')
        
        # Get bot service with settings from DB
        bot_service = get_client_bot_service()
        
        if not bot_service:
            self.stdout.write(
                self.style.ERROR(
                    'Client bot token not configured or bot is not active.\n'
                    'Please set up ClientBotSettings in Django Admin:\n'
                    '1. Go to /admin/telegram_bot/clientbotsettings/\n'
                    '2. Create settings with bot token from @BotFather\n'
                    '3. Set is_active=True'
                )
            )
            return
        
        self.stdout.write(self.style.SUCCESS('Client bot started! Press Ctrl+C to stop.'))
        
        try:
            bot_service.run()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nBot stopped by user.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Bot error: {e}'))
