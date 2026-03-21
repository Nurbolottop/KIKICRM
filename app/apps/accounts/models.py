from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.utils import timezone
from apps.common.utils.phone import normalize_phone


class UserRole(models.TextChoices):
    """Роли пользователей в системе CRM KIKI."""
    FOUNDER = 'FOUNDER', 'Основатель'
    MANAGER = 'MANAGER', 'Менеджер'
    OPERATOR = 'OPERATOR', 'Оператор'
    SMM = 'SMM', 'SMM'
    HR = 'HR', 'HR'
    SENIOR_CLEANER = 'SENIOR_CLEANER', 'Старший клинер'
    CLEANER = 'CLEANER', 'Клинер'


class UserManager(BaseUserManager):
    """Кастомный менеджер для модели User с phone в качестве основного поля."""

    def create_user(self, phone, password=None, **extra_fields):
        """Создает и возвращает обычного пользователя."""
        if not phone:
            raise ValueError('Телефон обязателен для создания пользователя')
        
        # Нормализация телефона
        try:
            phone = normalize_phone(phone)
        except ValueError:
            pass  # Если нормализация не удалась, оставляем как есть

        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', True)

        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        """Создает и возвращает суперпользователя."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', UserRole.FOUNDER)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True.')

        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Кастомная модель пользователя с phone-аутентификацией и ролями."""

    phone = models.CharField(
        'Телефон',
        max_length=20,
        unique=True,
        db_index=True,
        help_text='Основной телефон для входа (формат: +996XXXXXXXXX)'
    )
    full_name = models.CharField(
        'Полное имя',
        max_length=150,
        blank=True,
        default=''
    )
    role = models.CharField(
        'Роль',
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CLEANER,
        db_index=True
    )

    # Статусы Django
    is_staff = models.BooleanField(
        'Статус персонала',
        default=False,
        help_text='Определяет, может ли пользователь входить в админ-панель.'
    )
    is_active = models.BooleanField(
        'Активен',
        default=True,
        help_text='Определяет, активна ли учетная запись.'
    )
    is_superuser = models.BooleanField(
        'Статус суперпользователя',
        default=False,
        help_text='Определяет, имеет ли пользователь все разрешения.'
    )

    # Временные метки
    date_joined = models.DateTimeField(
        'Дата регистрации',
        default=timezone.now
    )

    objects = UserManager()

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-date_joined']

    def __str__(self):
        if self.full_name:
            return f'{self.full_name} ({self.phone})'
        return self.phone

    def get_short_name(self):
        """Возвращает короткое имя пользователя."""
        return self.full_name or self.phone

    def get_role_display_name(self):
        """Возвращает отображаемое название роли."""
        return self.get_role_display()

    @property
    def is_founder(self):
        return self.role == UserRole.FOUNDER

    @property
    def is_manager(self):
        return self.role == UserRole.MANAGER

    @property
    def is_operator(self):
        return self.role == UserRole.OPERATOR

    @property
    def is_hr(self):
        return self.role == UserRole.HR

    @property
    def is_senior_cleaner(self):
        return self.role == UserRole.SENIOR_CLEANER

    @property
    def is_cleaner(self):
        return self.role == UserRole.CLEANER

    def save(self, *args, **kwargs):
        """Нормализация телефона перед сохранением."""
        if self.phone:
            try:
                self.phone = normalize_phone(self.phone)
            except ValueError:
                pass  # Если нормализация не удалась, сохраняем как есть
        super().save(*args, **kwargs)
