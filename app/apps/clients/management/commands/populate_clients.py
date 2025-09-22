from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from random import choice, randint
from ...models import Client, ClientNote

User = get_user_model()

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
                'organization': 'ТОО "ТехноПром"',
                'phone': '87011234567',  # Казахстанский номер с 8
                'email': 'a.ivanov@example.com',
                'gender': 'male',
                'category': 'vip',
                'source': 'website',
                'address': 'г. Алматы, ул. Абая, 1',
                'whatsapp': '87011234567',
                'telegram_id': 'aivanov',
                'age': 35,
            },
            {
                'first_name': 'Елена',
                'last_name': 'Петрова',
                'organization': 'АО "КазТехноСервис"',
                'phone': '87771234567',  # Казахстанский номер с 8
                'email': 'e.petrova@example.com',
                'gender': 'female',
                'category': 'regular',
                'source': 'instagram',
                'address': 'г. Нур-Султан, пр. Мангилик Ел, 55',
                'whatsapp': '87771234567',
                'telegram_id': 'elena_petrova',
                'age': 28,
            },
            {
                'first_name': 'Айбек',
                'last_name': 'Кыдыров',
                'organization': 'ИП "Кыдыров А.К."',
                'phone': '0700123456',  # Кыргызский номер с 0
                'email': 'a.kydyrov@example.com',
                'gender': 'male',
                'category': 'vip',
                'source': 'referral',
                'address': 'г. Бишкек, ул. Чуй, 123',
                'whatsapp': '0700123456',
                'telegram_id': 'aibek_k',
                'age': 42,
            },
            {
                'first_name': 'Айгерим',
                'last_name': 'Каримова',
                'organization': 'ТОО "АстанаТрейд"',
                'phone': '87471234567',  # Казахстанский номер с 8
                'email': 'a.karimova@example.com',
                'gender': 'female',
                'category': 'regular',
                'source': 'website',
                'address': 'г. Шымкент, ул. Кабанбай батыра, 45',
                'whatsapp': '87471234567',
                'telegram_id': 'aigerim_k',
                'age': 31,
            },
            {
                'first_name': 'Нурлан',
                'last_name': 'Абдыкадыров',
                'organization': '',
                'phone': '0555123456',  # Кыргызский номер с 0
                'email': 'n.abdikadyrov@example.com',
                'gender': 'male',
                'category': 'new',
                'source': 'instagram',
                'address': 'г. Ош, ул. Ленина, 78',
                'whatsapp': '0555123456',
                'telegram_id': 'nurlan_a',
                'age': 25,
            },
            {
                'first_name': 'Айсулу',
                'last_name': 'Омарова',
                'organization': 'АО "КазАвтоПром"',
                'phone': '87771234568',  # Казахстанский номер с 8
                'email': 'a.omarova@example.com',
                'gender': 'female',
                'category': 'vip',
                'source': 'referral',
                'address': 'г. Актобе, пр. Абылай хана, 67',
                'whatsapp': '87771234568',
                'telegram_id': 'aisulu_o',
                'age': 38,
            },
            {
                'first_name': 'Арман',
                'last_name': 'Жумабаев',
                'organization': 'ТОО "ТехноСтарт"',
                'phone': '87021234567',  # Казахстанский номер с 8
                'email': 'a.zhumabayev@example.com',
                'gender': 'male',
                'category': 'regular',
                'source': 'website',
                'address': 'г. Караганда, ул. Ерубаева, 12',
                'whatsapp': '87021234567',
                'telegram_id': 'armanzh',
                'age': 33,
            },
            {
                'first_name': 'Айпери',
                'last_name': 'Асанова',
                'organization': 'ИП "Асанова А.К."',
                'phone': '0777123456',  # Кыргызский номер с 0
                'email': 'a.asanova@example.com',
                'gender': 'female',
                'category': 'new',
                'source': 'instagram',
                'address': 'г. Джалал-Абад, ул. Токтогула, 45',
                'whatsapp': '0777123456',
                'telegram_id': 'aiperi_a',
                'age': 27,
            },
            {
                'first_name': 'Данияр',
                'last_name': 'Садыков',
                'organization': 'ТОО "ОйлСервис"',
                'phone': '87051234567',  # Казахстанский номер с 8
                'email': 'd.sadykov@example.com',
                'gender': 'male',
                'category': 'vip',
                'source': 'referral',
                'address': 'г. Актау, 12-й микрорайон, д. 34',
                'whatsapp': '87051234567',
                'telegram_id': 'daniyar_s',
                'age': 45,
            },
            {
                'first_name': 'Айнур',
                'last_name': 'Искакова',
                'organization': 'АО "КазТрансОйл"',
                'phone': '87071234567',  # Казахстанский номер с 8
                'email': 'a.iskakova@example.com',
                'gender': 'female',
                'category': 'regular',
                'source': 'website',
                'address': 'г. Павлодар, ул. Ломова, 23',
                'whatsapp': '87071234567',
                'telegram_id': 'ainur_i',
                'age': 36,
            },
            {
                'first_name': 'Максат',
                'last_name': 'Абдуллаев',
                'organization': '',
                'phone': '0700123457',  # Кыргызский номер с 0
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
        created_count = 0
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

        for idx, client_data in enumerate(clients_data):
            # Set random dates for first and last order (within last year)
            days_ago = randint(1, 365)
            first_order = timezone.now() - timezone.timedelta(days=days_ago)
            last_order = first_order + timezone.timedelta(days=randint(1, days_ago))
            
            # Create client with additional fields
            client, created = Client.objects.get_or_create(
                phone=client_data['phone'],
                defaults={
                    'first_name': client_data['first_name'],
                    'last_name': client_data['last_name'],
                    'organization': client_data['organization'] or None,
                    'email': client_data['email'],
                    'gender': client_data['gender'],
                    'category': client_data['category'],
                    'source': client_data['source'],
                    'address': client_data['address'],
                    'whatsapp': client_data['whatsapp'],
                    'telegram_id': client_data['telegram_id'],
                    'age': client_data['age'],
                    'created_by': admin_user,
                    'updated_by': admin_user,
                    'first_order_date': first_order.date(),
                    'last_order_date': last_order.date(),
                    'orders_count': randint(1, 15),
                    'total_spent': randint(10000, 500000),
                }
            )
            
            if created:
                created_count += 1
                
                # Create a note for the client
                ClientNote.objects.create(
                    client=client,
                    text=sample_notes[idx],
                    created_by=admin_user
                )

        self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} clients'))
