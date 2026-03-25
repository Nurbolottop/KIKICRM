"""
Модели для управления инвентарем.
Складской учет: категории, товары, операции.
"""
from decimal import Decimal
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class InventoryItemType(models.TextChoices):
    """Тип инвентаря: крупный или мелкий."""
    LARGE = 'LARGE', 'Крупный'
    SMALL = 'SMALL', 'Мелкий'


class InventoryCategory(models.Model):
    """Категория инвентаря."""

    name = models.CharField(
        'Название',
        max_length=150,
        unique=True,
        help_text='Например: Химия, Инструменты, Расходники'
    )
    description = models.TextField(
        'Описание',
        blank=True,
        help_text='Опциональное описание категории'
    )
    is_active = models.BooleanField(
        'Активна',
        default=True,
        help_text='Неактивные категории не отображаются в списках'
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
        verbose_name = 'Категория инвентаря'
        verbose_name_plural = 'Категории инвентаря'
        ordering = ['name']

    def __str__(self):
        return self.name

    def active_items_count(self):
        """Возвращает количество активных товаров в категории."""
        return self.items.filter(is_active=True).count()


class InventoryItem(models.Model):
    """Товар/материал на складе."""

    name = models.CharField(
        'Название',
        max_length=200,
        unique=True,
        help_text='Название товара'
    )
    category = models.ForeignKey(
        InventoryCategory,
        on_delete=models.PROTECT,
        related_name='items',
        verbose_name='Категория'
    )
    item_type = models.CharField(
        'Тип инвентаря',
        max_length=20,
        choices=InventoryItemType.choices,
        default=InventoryItemType.SMALL,
        db_index=True,
        help_text='Крупный: техника и оборудование. Мелкий: расходники, тряпки, насадки и т.д.'
    )
    unit = models.CharField(
        'Единица измерения',
        max_length=50,
        default='шт',
        help_text='шт, литр, мл, упаковка, кг'
    )
    quantity = models.DecimalField(
        'Текущее количество',
        max_digits=15,
        decimal_places=3,
        default=0,
        help_text='Текущий остаток на складе'
    )
    min_quantity = models.DecimalField(
        'Минимальный остаток',
        max_digits=15,
        decimal_places=3,
        default=0,
        help_text='Критический минимум для алертов'
    )
    price_per_unit = models.DecimalField(
        'Цена за единицу',
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Закупочная цена за единицу'
    )
    is_active = models.BooleanField(
        'Активен',
        default=True,
        help_text='Неактивные товары скрыты из операций'
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
        verbose_name = 'Товар на складе'
        verbose_name_plural = 'Товары на складе'
        ordering = ['category', 'name']

    def __str__(self):
        return f'{self.name} ({self.quantity} {self.unit})'

    @property
    def is_large(self):
        return self.item_type == InventoryItemType.LARGE

    @property
    def is_small(self):
        return self.item_type == InventoryItemType.SMALL

    def is_low_stock(self):
        """Проверка на низкий остаток."""
        return self.quantity <= self.min_quantity

    def get_stock_status(self):
        """Возвращает статус запаса."""
        if self.quantity <= 0:
            return 'out', 'Нет на складе'
        if self.is_low_stock():
            return 'low', 'Низкий остаток'
        return 'ok', 'В наличии'

    def get_stock_value(self):
        """Возвращает стоимость запаса."""
        return self.quantity * self.price_per_unit


class TransactionType(models.TextChoices):
    """Типы операций со складом."""
    IN = 'IN', 'Приход'
    OUT = 'OUT', 'Списание'
    ADJUSTMENT = 'ADJUSTMENT', 'Корректировка'


class InventoryTransaction(models.Model):
    """Операция со складом (приход/списание/корректировка)."""

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='Товар'
    )
    transaction_type = models.CharField(
        'Тип операции',
        max_length=20,
        choices=TransactionType.choices,
        default=TransactionType.IN
    )
    quantity = models.DecimalField(
        'Количество',
        max_digits=15,
        decimal_places=3,
        help_text='Для списания используйте положительное число'
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_transactions',
        verbose_name='Заказ',
        help_text='Связанный заказ (для списаний)'
    )
    usage = models.ForeignKey(
        'orders.OrderInventoryUsage',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name='Строка использования',
        help_text='Связанная строка фактического использования инвентаря'
    )
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_transactions',
        verbose_name='Сотрудник',
        help_text='Кто выполнил операцию или использовал товар'
    )
    comment = models.TextField(
        'Комментарий',
        blank=True,
        help_text='Причина корректировки или детали операции'
    )
    created_at = models.DateTimeField(
        'Дата операции',
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Операция со складом'
        verbose_name_plural = 'Операции со складом'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_transaction_type_display()} — {self.item.name} ({self.quantity})'

    def clean(self):
        """Валидация перед сохранением."""
        from django.core.exceptions import ValidationError

        # Для списания проверяем достаточность остатка
        if self.transaction_type == TransactionType.OUT:
            if self.quantity > self.item.quantity:
                raise ValidationError(
                    f'Недостаточно товара на складе. '
                    f'Доступно: {self.item.quantity} {self.item.unit}, '
                    f'требуется: {self.quantity} {self.item.unit}'
                )

    def save(self, *args, **kwargs):
        """Сохранение с автоматическим обновлением остатков."""
        is_new = self._state.adding

        # Для новых записей обновляем остаток
        if is_new:
            self.clean()

        super().save(*args, **kwargs)

    def get_quantity_change(self):
        """Возвращает изменение остатка (+/-) для отображения."""
        if self.transaction_type == TransactionType.IN:
            return f'+{self.quantity}'
        elif self.transaction_type == TransactionType.OUT:
            return f'-{self.quantity}'
        else:
            sign = '+' if self.quantity >= 0 else ''
            return f'{sign}{self.quantity}'


@receiver(post_save, sender=InventoryTransaction)
def update_inventory_quantity(sender, instance, created, **kwargs):
    """
    Автоматически обновляет остаток товара после сохранения транзакции.
    """
    if created:
        item = instance.item
        quantity = instance.quantity

        if instance.transaction_type == TransactionType.IN:
            # Приход — увеличиваем остаток
            item.quantity += quantity
        elif instance.transaction_type == TransactionType.OUT:
            # Списание — уменьшаем остаток
            item.quantity -= quantity
        elif instance.transaction_type == TransactionType.ADJUSTMENT:
            # Корректировка — прибавляем значение (может быть отрицательным)
            item.quantity += quantity

        item.save(update_fields=['quantity', 'updated_at'])
