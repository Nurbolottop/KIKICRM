"""
Модели для приложения Клиенты.
"""
from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimestampMixin
from apps.core.utils import normalize_phone


class Client(TimestampMixin, models.Model):
    """
    Модель клиента.
    """

    class ClientCategory(models.TextChoices):
        """Категории клиентов."""
        INDIVIDUAL = 'individual', _('Физическое лицо')
        COMPANY = 'company', _('Компания')
        VIP = 'vip', _('VIP')

    class ClientSource(models.TextChoices):
        """Источники клиентов."""
        WEBSITE = 'website', _('Сайт')
        INSTAGRAM = 'instagram', _('Instagram')
        REFERRAL = 'referral', _('Рекомендация')
        OTHER = 'other', _('Другое')

    class Gender(models.TextChoices):
        """Пол клиента."""
        MALE = 'male', _('Мужской')
        FEMALE = 'female', _('Женский')
        UNSPECIFIED = 'unspecified', _('Не указан')

    # Фотография
    photo = models.ImageField(
        _('Фотография'),
        upload_to='clients/',
        null=True,
        blank=True
    )

    # Основная информация
    last_name = models.CharField(
        _('Фамилия'),
        max_length=150,
        blank=True
    )

    first_name = models.CharField(
        _('Имя'),
        max_length=150,
        blank=True
    )

    middle_name = models.CharField(
        _('Отчество'),
        max_length=150,
        blank=True
    )

    organization = models.CharField(
        _('Организация'),
        max_length=255,
        blank=True
    )

    # Классификация
    category = models.CharField(
        _('Категория'),
        max_length=20,
        choices=ClientCategory.choices,
        default=ClientCategory.INDIVIDUAL
    )

    source = models.CharField(
        _('Источник'),
        max_length=20,
        choices=ClientSource.choices,
        default=ClientSource.WEBSITE
    )

    gender = models.CharField(
        _('Пол'),
        max_length=15,
        choices=Gender.choices,
        default=Gender.UNSPECIFIED
    )

    # Контактные данные
    phone = models.CharField(
        _('Телефон'),
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\+?[\d\s\-\(\)]+$',
                message=_('Введите корректный номер телефона')
            )
        ]
    )

    phone_secondary = models.CharField(
        _('Дополнительный телефон'),
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?[\d\s\-\(\)]+$',
                message=_('Введите корректный номер телефона')
            )
        ]
    )

    whatsapp = models.CharField(
        _('WhatsApp'),
        max_length=20,
        blank=True
    )

    email = models.EmailField(
        _('Email'),
        blank=True
    )

    # Дополнительная информация
    birth_date = models.DateField(
        _('Дата рождения'),
        null=True,
        blank=True
    )

    address = models.CharField(
        _('Адрес'),
        max_length=255,
        blank=True
    )

    notes = models.TextField(
        _('Примечания'),
        blank=True
    )

    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_clients',
        verbose_name=_('Кем создан')
    )

    class Meta:
        verbose_name = _('Клиент')
        verbose_name_plural = _('Клиенты')
        ordering = ['-created_at']

    def __str__(self):
        full_name = self.get_full_name()
        if self.organization:
            return f"{full_name} ({self.organization})"
        return full_name

    def get_full_name(self):
        """Возвращает полное имя клиента."""
        parts = [self.last_name, self.first_name, self.middle_name]
        return ' '.join(filter(None, parts))

    def save(self, *args, **kwargs):
        # Нормализация телефона
        if self.phone:
            self.phone = normalize_phone(self.phone)
        if self.phone_secondary:
            self.phone_secondary = normalize_phone(self.phone_secondary)
        if self.whatsapp:
            self.whatsapp = normalize_phone(self.whatsapp)
        super().save(*args, **kwargs)

    def get_avatar_url(self):
        """Возвращает URL аватара клиента."""
        if self.photo:
            return self.photo.url
        # Возвращаем дефолтный аватар на основе пола
        if self.gender == self.Gender.MALE:
            return '/static/images/man-icon.png'
        elif self.gender == self.Gender.FEMALE:
            return '/static/images/girl-icon.png'
        return '/static/images/other-icon.png'


class ClientNote(TimestampMixin, models.Model):
    client = models.ForeignKey(
        'clients.Client',
        on_delete=models.CASCADE,
        related_name='notes_list',
        verbose_name=_('Клиент')
    )
    author = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='client_notes',
        verbose_name=_('Автор')
    )
    text = models.TextField(_('Текст заметки'))

    class Meta:
        verbose_name = _('Заметка клиента')
        verbose_name_plural = _('Заметки клиентов')
        ordering = ['-created_at']
