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
    room_count = models.PositiveIntegerField(
        'Количество комнат',
        default=1,
        help_text='Для квартир: 1, 2, 3 и т.д. комнат'
    )
    senior_cleaner_count = models.PositiveIntegerField(
        'Кол-во ст. клинеров',
        default=1,
        help_text='Рекомендуемое количество старших клинеров'
    )
    cleaner_count = models.PositiveIntegerField(
        'Кол-во клинеров',
        default=2,
        help_text='Рекомендуемое количество обычных клинеров'
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

    def get_inventory_templates(self):
        return self.inventory_templates.select_related('inventory_item', 'inventory_item__category').order_by(
            'inventory_item__item_type', 'inventory_item__category__name', 'inventory_item__name'
        )


class ServiceInventoryTemplate(models.Model):
    """Шаблон рекомендуемого инвентаря для услуги."""

    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='inventory_templates',
        verbose_name='Услуга'
    )
    inventory_item = models.ForeignKey(
        'inventory.InventoryItem',
        on_delete=models.CASCADE,
        related_name='service_templates',
        verbose_name='Инвентарь'
    )
    quantity = models.DecimalField(
        'Рекомендуемое количество',
        max_digits=12,
        decimal_places=3,
        default=0
    )
    note = models.CharField(
        'Примечание',
        max_length=255,
        blank=True,
        default=''
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Шаблон инвентаря услуги'
        verbose_name_plural = 'Шаблоны инвентаря услуг'
        ordering = ['inventory_item__item_type', 'inventory_item__name']
        unique_together = ('service', 'inventory_item')

    def __str__(self):
        return f'{self.service.name} — {self.inventory_item.name} ({self.quantity})'


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
