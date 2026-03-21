from django.db import models

from apps.common.models import BaseModel


class Service(BaseModel):
    """Модель услуги CRM KIKI."""

    name = models.CharField(
        'Название услуги',
        max_length=150
    )
    description = models.TextField(
        'Описание',
        blank=True
    )
    image = models.ImageField(
        'Фото услуги',
        upload_to='services/',
        blank=True,
        null=True
    )
    price = models.DecimalField(
        'Цена',
        max_digits=10,
        decimal_places=2
    )
    cleaner_salary = models.DecimalField(
        'ЗП клинеру',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    senior_cleaner_salary = models.DecimalField(
        'ЗП ст. клинеру',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    senior_cleaner_bonus = models.DecimalField(
        'Доп. оплата ст. клинеру',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    service_deadline_hours = models.DecimalField(
        'Дедлайн услуги (часы)',
        max_digits=10,
        decimal_places=2,
        default=0
    )
    checklist = models.JSONField(
        'Чеклист задач',
        default=list,
        blank=True,
        help_text='Список задач которые выполняются в рамках услуги'
    )
    is_active = models.BooleanField(
        'Активна',
        default=True
    )

    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.price} сом)'

    def get_checklist_display(self):
        """Возвращает чеклист для отображения."""
        if not self.checklist:
            return []
        return self.checklist


class ExtraService(BaseModel):
    """Модель дополнительной услуги (доп. опции к заказу)."""

    name = models.CharField(
        'Название доп. услуги',
        max_length=150
    )
    description = models.TextField(
        'Описание',
        blank=True
    )
    price = models.DecimalField(
        'Цена',
        max_digits=10,
        decimal_places=2,
        help_text='Цена в сомах'
    )
    is_active = models.BooleanField(
        'Активна',
        default=True
    )

    class Meta:
        verbose_name = 'Дополнительная услуга'
        verbose_name_plural = 'Дополнительные услуги'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.price} сом)'
