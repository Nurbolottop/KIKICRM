import random
import string
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import re

User = get_user_model()

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
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    
    @classmethod
    def validate_whatsapp_number(cls, value):
        """
        Валидация номера WhatsApp для Казахстана и Кыргызстана.
        Принимает номера в форматах: 77001234567, +77001234567, 7 (700) 123-45-67, 0555123456, +996555123456
        """
        if not value:
            return value
            
        # Удаляем все нецифровые символы
        digits = re.sub(r'\D', '', str(value))
        
        # Проверяем казахстанские номера (начинаются с 7 или 8, 11 цифр)
        if len(digits) == 11 and digits[0] in ('7', '8'):
            # Конвертируем 8 в 7 для казахстанских номеров
            return '7' + digits[1:] if digits[0] == '8' else digits
            
        # Проверяем кыргызские номера (начинаются с 996 или 0, 9-12 цифр)
        if digits.startswith('996'):
            if len(digits) == 12:  # 996555123456
                return digits[3:]  # Возвращаем без кода страны
            elif len(digits) == 10:  # 0555123456
                return digits[1:] if digits.startswith('0') else digits
        elif digits.startswith('0'):
            if len(digits) == 10:  # 0555123456
                return digits[1:]
            elif len(digits) == 9:  # 555123456
                return digits
                
        # Если номер не соответствует ни одному из форматов
        raise ValidationError('Введите корректный номер телефона (Казахстан: 7XXXXXXXXXX или Кыргызстан: 0XXXXXXXXX)')

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
        self._whatsapp_number = self.validate_whatsapp_number(value) if value else None
    telegram_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="Telegram ID")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Адрес")
    organization = models.CharField(max_length=255, blank=True, null=True, verbose_name="Организация")
    age = models.PositiveIntegerField(blank=True, null=True, verbose_name="Возраст")
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

    def save(self, *args, **kwargs):
        # Generate a client ID if this is a new client
        if not self.client_id:
            self.client_id = self.generate_unique_client_id()
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
