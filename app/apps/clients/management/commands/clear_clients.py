from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Удаляет все таблицы приложения clients (без пересоздания)'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Get all tables for the clients app
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE 'clients_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            if not tables:
                self.stdout.write(self.style.WARNING("Не найдено таблиц для удаления."))
                return

            # Drop all client-related tables
            self.stdout.write("Удаление таблиц приложения clients...")
            cursor.execute(f"DROP TABLE IF EXISTS {', '.join(tables)} CASCADE;")
            
            self.stdout.write(self.style.SUCCESS(f"Удалены таблицы: {', '.join(tables)}"))

        # Clear migrations
        self.stdout.write("Очистка истории миграций...")
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM django_migrations WHERE app = 'clients';")
        
        self.stdout.write(
            self.style.SUCCESS("Готово! Все таблицы clients удалены. Вы можете применить миграции заново.")
        )