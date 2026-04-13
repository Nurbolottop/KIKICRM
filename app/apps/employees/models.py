from django.db import models
from django.conf import settings
from django.utils import timezone


class EmployeeStatus(models.TextChoices):
    """Статусы сотрудника в системе."""
    ACTIVE = 'ACTIVE', 'Активен'
    INACTIVE = 'INACTIVE', 'Неактивен'
    ON_LEAVE = 'ON_LEAVE', 'В отпуске'
    FIRED = 'FIRED', 'Уволен'
    CANDIDATE = 'CANDIDATE', 'Кандидат'


class Employee(models.Model):
    """Базовая модель сотрудника с привязкой к пользователю."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employee',
        verbose_name='Пользователь'
    )
    employee_code = models.CharField(
        'Код сотрудника',
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        help_text='Уникальный код сотрудника (можно назначить позже)'
    )
    phone_secondary = models.CharField(
        'Дополнительный телефон',
        max_length=20,
        blank=True,
        default='',
        help_text='Второй номер телефона для связи'
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='employees/avatars/',
        blank=True,
        null=True
    )
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=EmployeeStatus.choices,
        default=EmployeeStatus.CANDIDATE,
        db_index=True
    )
    hire_date = models.DateField(
        'Дата приема',
        blank=True,
        null=True
    )
    contract_term = models.IntegerField(
        'Срок найма',
        choices=[
            (3, '3 месяца'),
            (6, '6 месяцев'),
            (12, '1 год'),
        ],
        blank=True,
        null=True,
        help_text='Срок действия договора в месяцах'
    )
    contract_end_date = models.DateField(
        'Дата окончания контракта',
        blank=True,
        null=True,
        help_text='Автоматически рассчитывается на основе даты приема и срока найма'
    )
    contract_file = models.FileField(
        'Файл договора',
        upload_to='employees/contracts/',
        blank=True,
        null=True,
        help_text='Загрузите скан или фото договора'
    )
    
    # Паспортные данные (вынесены в основную модель для удобства)
    passport_type = models.CharField(
        'Тип документа',
        max_length=20,
        choices=[
            ('PASSPORT', 'Паспорт'),
            ('ID_CARD', 'ID карта'),
            ('CERTIFICATE', 'Свидетельство'),
            ('OTHER', 'Другой документ'),
        ],
        default='PASSPORT',
        blank=True
    )
    passport_number = models.CharField(
        'Номер документа',
        max_length=50,
        blank=True,
        default=''
    )
    passport_issued_by = models.CharField(
        'Кем выдан',
        max_length=255,
        blank=True,
        default=''
    )
    passport_issue_date = models.DateField(
        'Дата выдачи',
        blank=True,
        null=True
    )
    passport_expiry_date = models.DateField(
        'Дата окончания срока',
        blank=True,
        null=True
    )
    passport_photo_front = models.ImageField(
        'Фото паспорта (передняя сторона)',
        upload_to='employees/passports/',
        blank=True,
        null=True,
        help_text='Фото передней стороны паспорта/ID карты'
    )
    passport_photo_back = models.ImageField(
        'Фото паспорта (задняя сторона)',
        upload_to='employees/passports/',
        blank=True,
        null=True,
        help_text='Фото задней стороны паспорта/ID карты'
    )
    fire_date = models.DateField(
        'Дата увольнения',
        blank=True,
        null=True
    )
    notes = models.TextField(
        'Заметки',
        blank=True,
        default='',
        help_text='Внутренние заметки о сотруднике'
    )
    is_blacklisted = models.BooleanField(
        'В черном списке',
        default=False,
        db_index=True
    )
    deactivation_reason = models.TextField(
        'Причина деактивации',
        blank=True,
        default=''
    )
    firing_reason = models.TextField(
        'Причина увольнения',
        blank=True,
        default=''
    )

    # Временные метки
    created_at = models.DateTimeField(
        'Дата создания',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'Дата обновления',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'
        ordering = ['-created_at']

    def __str__(self):
        user_str = str(self.user) if self.user else 'Нет пользователя'
        if self.employee_code:
            return f'{user_str} [{self.employee_code}]'
        return user_str

    def get_user_full_name(self):
        """Возвращает полное имя связанного пользователя."""
        return self.user.full_name if self.user else ''

    def get_user_phone(self):
        """Возвращает телефон связанного пользователя."""
        return self.user.phone if self.user else ''

    def get_user_role(self):
        """Возвращает роль связанного пользователя."""
        return self.user.role if self.user else None

    @property
    def is_active_employee(self):
        """Проверяет, является ли сотрудник активным."""
        return self.status == EmployeeStatus.ACTIVE

    @property
    def can_work(self):
        """Проверяет, может ли сотрудник выполнять работу."""
        return self.status in [EmployeeStatus.ACTIVE, EmployeeStatus.ON_LEAVE]


class EmployeeEarning(models.Model):
    """Начисление сотруднику за выполненный заказ."""

    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='earnings',
        verbose_name='Сотрудник'
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='employee_earnings',
        verbose_name='Заказ'
    )
    role_on_order = models.CharField(
        'Роль в заказе',
        max_length=100,
        blank=True
    )
    amount = models.DecimalField(
        'Сумма',
        max_digits=10,
        decimal_places=2
    )
    earned_at = models.DateTimeField(
        'Дата начисления',
        default=timezone.now,
        db_index=True
    )
    is_paid = models.BooleanField(
        'Оплачено',
        default=False,
        db_index=True
    )
    paid_at = models.DateTimeField(
        'Дата оплаты',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Начисление сотруднику'
        verbose_name_plural = 'Начисления сотрудникам'
        ordering = ['-earned_at']
        unique_together = ['employee', 'order']

    def __str__(self):
        return f'{self.employee} — {self.amount} сом (#{self.order.order_code or self.order.id})'


class DocumentType(models.TextChoices):
    """Типы документов удостоверяющих личность."""
    PASSPORT = 'PASSPORT', 'Паспорт'
    ID_CARD = 'ID_CARD', 'ID карта'
    CERTIFICATE = 'CERTIFICATE', 'Свидетельство'
    OTHER = 'OTHER', 'Другой документ'


class EmployeeDocument(models.Model):
    """Документы сотрудника (паспорт, удостоверение и т.д.)."""

    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Сотрудник'
    )
    document_type = models.CharField(
        'Тип документа',
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.PASSPORT
    )
    document_number = models.CharField(
        'Номер документа',
        max_length=50,
        blank=True,
        default='',
        help_text='Номер паспорта или другого документа'
    )
    file = models.FileField(
        'Файл документа',
        upload_to='employees/documents/%Y/%m/',
        help_text='Скан или фото документа'
    )
    issued_by = models.CharField(
        'Кем выдан',
        max_length=255,
        blank=True,
        default='',
        help_text='Орган, выдавший документ'
    )
    issue_date = models.DateField(
        'Дата выдачи',
        blank=True,
        null=True
    )
    expiry_date = models.DateField(
        'Дата окончания срока',
        blank=True,
        null=True,
        help_text='Для паспортов и других документов со сроком действия'
    )
    is_active = models.BooleanField(
        'Активен',
        default=True,
        help_text='Основной/действующий документ'
    )
    notes = models.TextField(
        'Заметки',
        blank=True,
        default='',
        help_text='Дополнительная информация о документе'
    )
    created_at = models.DateTimeField(
        'Дата создания',
        auto_now_add=True
    )
    updated_at = models.DateTimeField(
        'Дата обновления',
        auto_now=True
    )

    class Meta:
        verbose_name = 'Документ сотрудника'
        verbose_name_plural = 'Документы сотрудников'
        ordering = ['-is_active', '-created_at']

    def __str__(self):
        doc_type = self.get_document_type_display()
        if self.document_number:
            return f'{self.employee} — {doc_type} №{self.document_number}'
        return f'{self.employee} — {doc_type}'
