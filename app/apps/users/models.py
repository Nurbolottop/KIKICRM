from django.db import models
from django.contrib.auth.models import AbstractUser
from django_resized.forms import ResizedImageField
from django.core.validators import RegexValidator
from django.utils.html import format_html

phone_validator = RegexValidator(
    regex=r'^(\+996\d{9}|996\d{9})$',
    message="Номер должен быть в формате +996xxxxxxxxx или 996xxxxxxxxx"
)

class User(AbstractUser):
    class Role(models.TextChoices):
        IT = "IT", "IT Отдел"
        FOUNDER = 'FOUNDER', 'Основатель'
        SMM = 'SMM', 'СММ-менеджер'
        OPERATOR = 'OPERATOR', 'Оператор'
        MANAGER = 'MANAGER', 'Менеджер'
        SENIOR_CLEANER = 'SENIOR_CLEANER', 'Старший клинер'
        CLEANER = 'CLEANER', 'Клинер'
        CANDIDATE = 'CANDIDATE', 'Кандидат'

    role = models.CharField(
        max_length=50, choices=Role.choices, default=Role.CANDIDATE, verbose_name="Роль"
    )
    avatar = ResizedImageField(
        force_format="WEBP", quality=100, upload_to='users_avatars/', verbose_name="Логотип"
    )
    full_name = models.CharField(max_length=100, verbose_name="Полное имя")
    phone = models.CharField(max_length=100, blank=True, verbose_name="Номер телефона")
    whatsapp = models.CharField(
        max_length=100, blank=True, verbose_name="WhatsApp",
        validators=[phone_validator],
        help_text="Введите номер в формате +996558000350 или 996558000350"
    )
    telegram_id = models.BigIntegerField(null=True, blank=True, verbose_name="Telegram ID")

    def whatsapp_link(self):
        if self.whatsapp:
            number = self.whatsapp.replace('+', '')
            url = f"https://wa.me/{number}"
            return format_html('<a href="{}" target="_blank">Открыть чат</a>', url)
        return '-'

    whatsapp_link.short_description = 'WhatsApp'

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ['-date_joined']

