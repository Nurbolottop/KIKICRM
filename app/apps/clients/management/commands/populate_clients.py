import random
import string
from random import randint
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from ...models import Client, ClientNote

User = get_user_model()

def generate_client_id():
    """Generate a random 5-character alphanumeric ID"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

class Command(BaseCommand):
    help = 'Populates the database with sample client data'

    def handle(self, *args, **options):
        # Get or create a superuser to be the creator
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )

        # Sample data for clients
        clients_data = [
            {
                'first_name': 'Александр',
                'last_name': 'Иванов',
                'middle_name': 'Сергеевич',
                'organization': 'ТОО "ТехноПром"',
                'phone': '87011234567',
                'email': 'a.ivanov@example.com',
                'gender': 'male',
                'category': 'vip',
                'source': 'website',
                'address': 'г. Алматы, ул. Абая, 1',
                'whatsapp': '87011234567',
                'telegram_id': 'aivanov',
                'age': 35,
                'client_id': 'A1B2C',
                'created_by': admin_user,
                'updated_by': admin_user
            },
            {
                'first_name': 'Елена',
                'last_name': 'Петрова',
                'middle_name': 'Игоревна',
                'organization': 'АО "КазТехноСервис"',
                'phone': '87771234567',
                'email': 'e.petrova@example.com',
                'gender': 'female',
                'category': 'regular',
                'source': 'instagram',
                'address': 'г. Нур-Султан, пр. Мангилик Ел, 55',
                'whatsapp': '87771234567',
                'telegram_id': 'elena_petrova',
                'age': 28,
                'client_id': 'D3E4F',
                'created_by': admin_user,
                'updated_by': admin_user
            },
            {
                'first_name': 'Айбек',
                'last_name': 'Кыдыров',
                'middle_name': 'Темирбекович',
                'organization': 'ИП "Кыдыров А.К."',
                'phone': '0700123456',
                'email': 'a.kydyrov@example.com',
                'gender': 'male',
                'category': 'vip',
                'source': 'referral',
                'address': 'г. Бишкек, ул. Чуй, 123',
                'whatsapp': '0700123456',
                'telegram_id': 'aibek_k',
                'age': 42,
                'client_id': 'G5H6I',
                'created_by': admin_user,
                'updated_by': admin_user
            },
            {
                'first_name': 'Айгерим',
                'last_name': 'Каримова',
                'middle_name': 'Сериковна',
                'organization': 'ТОО "АстанаТрейд"',
                'phone': '87471234567',
                'email': 'a.karimova@example.com',
                'gender': 'female',
                'category': 'regular',
                'source': 'website',
                'address': 'г. Шымкент, ул. Кабанбай батыра, 45',
                'whatsapp': '87471234567',
                'telegram_id': 'aigerim_k',
                'age': 31,
                'client_id': 'J7K8L',
                'created_by': admin_user,
                'updated_by': admin_user
            },
            {
                'first_name': 'Нурлан',
                'last_name': 'Абдыкадыров',
                'middle_name': 'Алибекович',
                'organization': '',
                'phone': '0555123456',
                'email': 'n.abdikadyrov@example.com',
                'gender': 'male',
                'category': 'new',
                'source': 'instagram',
                'address': 'г. Ош, ул. Ленина, 78',
                'whatsapp': '0555123456',
                'telegram_id': 'nurlan_a',
                'age': 25,
                'client_id': 'M9N0P',
                'created_by': admin_user,
                'updated_by': admin_user
            },
            {
                'first_name': 'Айсулу',
                'last_name': 'Омарова',
                'middle_name': 'Канатовна',
                'organization': 'АО "КазАвтоПром"',
                'phone': '87771234568',
                'email': 'a.omarova@example.com',
                'gender': 'female',
                'category': 'vip',
                'source': 'referral',
                'address': 'г. Актобе, пр. Абылай хана, 1',
                'whatsapp': '87771234568',
                'telegram_id': 'aisulu_o',
                'age': 29,
                'client_id': 'Q1R2S',
                'created_by': admin_user,
                'updated_by': admin_user
            },
            {
                'first_name': 'Арман',
                'last_name': 'Жумабаев',
                'middle_name': 'Аскарович',
                'organization': 'ТОО "ТехноСтарт"',
                'phone': '87021234567',
                'email': 'a.zhumabayev@example.com',
                'gender': 'male',
                'category': 'regular',
                'source': 'website',
                'address': 'г. Караганда, ул. Ерубаева, 12',
                'whatsapp': '87021234567',
                'telegram_id': 'armanzh',
                'age': 33,
                'client_id': 'T3U4V',
                'created_by': admin_user,
                'updated_by': admin_user
            },
            {
                'first_name': 'Айпери',
                'last_name': 'Асанова',
                'middle_name': 'Кубанычбековна',
                'organization': 'ИП "Асанова А.К."',
                'phone': '0777123456',
                'email': 'a.asanova@example.com',
                'gender': 'female',
                'category': 'new',
                'source': 'instagram',
                'address': 'г. Джалал-Абад, ул. Токтогула, 45',
                'whatsapp': '0777123456',
                'telegram_id': 'aiperi_a',
                'age': 27,
                'client_id': 'W5X6Y',
                'created_by': admin_user,
                'updated_by': admin_user
            },
            {
                'first_name': 'Данияр',
                'last_name': 'Садыков',
                'middle_name': 'Рашидович',
                'organization': 'ТОО "ОйлСервис"',
                'phone': '87051234567',
                'email': 'd.sadykov@example.com',
                'gender': 'male',
                'category': 'vip',
                'source': 'referral',
                'address': 'г. Актау, 12-й микрорайон, д. 34',
                'whatsapp': '87051234567',
                'telegram_id': 'daniyar_s',
                'age': 45,
                'client_id': 'Z7A8B',
                'created_by': admin_user,
                'updated_by': admin_user
            },
            {
                'first_name': 'Айнур',
                'last_name': 'Искакова',
                'middle_name': 'Маратовна',
                'organization': 'АО "КазТрансОйл"',
                'phone': '87071234567',
                'email': 'a.iskakova@example.com',
                'gender': 'female',
                'category': 'regular',
                'source': 'website',
                'address': 'г. Павлодар, ул. Ломова, 23',
                'whatsapp': '87071234567',
                'telegram_id': 'ainur_i',
                'age': 36,
                'client_id': 'C9D0E',
                'created_by': admin_user,
                'updated_by': admin_user
            },
            {
                'first_name': 'Максат',
                'last_name': 'Абдуллаев',
                'middle_name': 'Темирланович',
                'organization': '',
                'phone': '0700123457',
                'email': 'm.abdullayev@example.com',
                'gender': 'male',
                'category': 'new',
                'source': 'instagram',
                'address': 'г. Балыкчи, ул. Советская, 12',
                'whatsapp': '0700123457',
                'telegram_id': 'maksat_a',
                'age': 29,
            }
        ]

        # Create clients
        clients_created = 0
        
        # Sample notes for clients
        sample_notes = [
            "Клиент заинтересован в оптовой закупке. Требуется перезвонить 25.09",
            "Постоянный клиент, заказывает каждые 2 недели. Любит скидки",
            "Нужно отправить коммерческое предложение на почту",
            "VIP клиент, обращаться на Вы. Любит персональный подход",
            "Интересуются новыми поступлениями. Отправить уведомление при появлении",
            "Была претензия по качеству. Решено сделать скидку 10% на след заказ",
            "Корпоративный клиент. Оплата по безналичному расчету",
            "Нужно уточнить размеры перед следующим заказом",
            "Любит получать информацию о скидках в первую очередь",
            "Рекомендован клиентом с номером +77011234567",
            "Требуется консультация по ассортименту. Перезвонить завтра в 15:00"
        ]

        for client_data in clients_data:
            try:
                # Generate a unique client_id if not provided
                if not client_data.get('client_id'):
                    while True:
                        new_id = generate_client_id()
                        if not Client.objects.filter(client_id=new_id).exists():
                            client_data['client_id'] = new_id
                            break
                
                # Create the client
                client = Client.objects.create(**client_data)
                clients_created += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Создан клиент: {client.last_name} {client.first_name} (ID: {client.client_id})')
                )
                
                # Add some sample notes for the client
                num_notes = random.randint(1, 3)
                for _ in range(num_notes):
                    note_text = random.choice(sample_notes)
                    ClientNote.objects.create(
                        client=client,
                        text=note_text,
                        created_by=admin_user
                    )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Ошибка при создании клиента {client_data.get("last_name")} {client_data.get("first_name")}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nГотово! Создано {clients_created} клиентов с заметками.')
        )
