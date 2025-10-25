import random
import string
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import re

User = get_user_model()

def validate_phone_number(value):
    """
    Валидация номера телефона для Казахстана и Кыргызстана.
    """
    if not value:
        return

    digits = re.sub(r'\D', '', str(value))

    # Казахстан: 11 цифр, начинается с 7 или 8
    is_kz = len(digits) == 11 and digits.startswith(('7', '8'))
    # Кыргызстан: 10 цифр, начинается с 0, или 12 цифр с 996, или 9 цифр без 0
    is_kg = (len(digits) == 10 and digits.startswith('0')) or \
            (len(digits) == 12 and digits.startswith('996')) or \
            (len(digits) == 9 and not digits.startswith('0'))

    if not (is_kz or is_kg):
        raise ValidationError('Введите корректный номер телефона (Казахстан: 7/8... или Кыргызстан: 0...)')

class Client(models.Model):
    GENDER_CHOICES = [
        ("male", "Мужской"),
        ("female", "Женский"),
        ("other", "Другое"),
    ]

    CATEGORY_CHOICES = [
        ("new", "Новый"),
        ("regular", "Постоянный"),
        ("lost", "Потерянный"),
        ("vip", "VIP"),
        ("other", "Другой"),
    ]

    SOURCE_CHOICES = [
        ("instagram", "Instagram"),
        ("website", "Сайт"),
        ("referral", "Сарафанное радио"),
        ("other", "Другое"),
    ]

    # 📁 Основные данные
    client_id = models.CharField(
        max_length=5, 
        unique=True, 
        blank=True,
        verbose_name="ID клиента",
        help_text="Уникальный 5-значный идентификатор клиента"
    )
    photo = models.ImageField(upload_to="clients/photos/", blank=True, null=True, verbose_name="Фото")
    first_name = models.CharField(max_length=100, verbose_name="Имя")
    last_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Фамилия")
    middle_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="Отчество")
    phone = models.CharField(max_length=20, verbose_name="Телефон", validators=[validate_phone_number])
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    
    _whatsapp_number = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        verbose_name="WhatsApp номер",
        help_text="Введите номер телефона в международном формате (например: 555123456 или 0555123456)",
        db_column='whatsapp_number'  # Store the raw number in the database
    )
    
    @property
    def whatsapp(self):
        """Return the WhatsApp link"""
        return self.get_whatsapp_link(self._whatsapp_number)
        
    @whatsapp.setter
    def whatsapp(self, value):
        """Set the WhatsApp number with validation"""
        if value:
            validate_phone_number(value)  # Validate before setting
            self._whatsapp_number = value
        else:
            self._whatsapp_number = None
    telegram_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="Telegram ID")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Адрес")
    organization = models.CharField(max_length=255, blank=True, null=True, verbose_name="Организация")
    birth_date = models.DateField(blank=True, null=True, verbose_name="Дата рождения")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True, verbose_name="Пол")

    # 🔹 Классификация
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="new", verbose_name="Категория")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="other", verbose_name="Канал привлечения")

    # 🔹 Аналитика заказов
    orders_count = models.PositiveIntegerField(default=0, verbose_name="Количество заказов")
    first_order_date = models.DateField(blank=True, null=True, verbose_name="Дата первого заказа")
    last_order_date = models.DateField(blank=True, null=True, verbose_name="Дата последнего заказа")
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Общая сумма заказов")

    # 🔹 Служебные поля
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="clients_created",
        verbose_name="Кем добавлен"
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="clients_updated",
        verbose_name="Кем изменен"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Когда добавлен")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Когда изменен")

    def get_whatsapp_link(self, phone_number):
        """Конвертирует номер телефона в ссылку WhatsApp"""
        if not phone_number:
            return ''
            
        # Удаляем все нецифровые символы
        digits = re.sub(r'\D', '', str(phone_number))
        
        # Обрабатываем казахстанские номера
        if digits.startswith('7') and len(digits) == 11:
            return f'https://wa.me/{digits}'
            
        # Обрабатываем кыргызские номера
        if digits.startswith('996') and len(digits) == 12:
            return f'https://wa.me/{digits}'
            
        # Если формат не распознан, возвращаем как есть (на случай будущих изменений)
        return f'https://wa.me/{digits}'

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''} ({self.phone})"

    @property
    def whatsapp_link(self):
        """Генерирует ссылку для WhatsApp"""
        if self.whatsapp:
            return f"https://wa.me/{self.whatsapp.replace('+','').replace(' ','')}"
        return None

    def generate_unique_client_id(self):
        """Generate a unique 5-character alphanumeric ID"""
        while True:
            # Generate a random 5-character string (uppercase letters and digits)
            client_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            # Check if this ID already exists
            if not Client.objects.filter(client_id=client_id).exists():
                return client_id

    def _clean_phone_number(self, number):
        if not number:
            return None
        digits = re.sub(r'\D', '', str(number))
        # KZ: 87... -> 77...
        if len(digits) == 11 and digits.startswith('8'):
            return '7' + digits[1:]
        # KG: 0555... -> 555...
        if len(digits) == 10 and digits.startswith('0'):
            return digits[1:]
        # KG: 996555... -> 555...
        if len(digits) == 12 and digits.startswith('996'):
            return digits[3:]
        return digits

    def save(self, *args, **kwargs):
        # Generate a client ID if this is a new client
        if not self.client_id:
            self.client_id = self.generate_unique_client_id()
        
        # Clean phone numbers before saving
        self.phone = self._clean_phone_number(self.phone)
        if self._whatsapp_number:
            self._whatsapp_number = self._clean_phone_number(self._whatsapp_number)

        super().save(*args, **kwargs)

    class Meta: 
        verbose_name = "Клиент"
        verbose_name_plural = "Клиенты"

class ClientNote(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="notes")
    text = models.TextField(verbose_name="Заметка")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Кем добавлена")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Когда добавлена")

    def __str__(self):
        return f"Заметка для {self.client} ({self.created_at:%d.%m.%Y})"
