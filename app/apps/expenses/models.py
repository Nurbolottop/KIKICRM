from django.db import models
from django.utils import timezone


class ExpenseCategory(models.TextChoices):
    """Категории расходов сотрудников."""
    CHEMICALS = 'CHEMICALS', 'Химия'
    TRANSPORT = 'TRANSPORT', 'Транспорт'
    TOOLS = 'TOOLS', 'Инструменты'
    CONSUMABLES = 'CONSUMABLES', 'Расходники'
    RENT = 'RENT', 'Аренда'
    UTILITIES = 'UTILITIES', 'Коммунальные услуги'
    OFFICE = 'OFFICE', 'Офисные расходы'
    MARKETING = 'MARKETING', 'Маркетинг'
    OTHER = 'OTHER', 'Другое'


class Expense(models.Model):
    """Модель расхода сотрудника."""
    
    employee = models.ForeignKey(
        'employees.Employee',
        on_delete=models.CASCADE,
        related_name='expenses',
        verbose_name='Сотрудник',
        null=True,
        blank=True  # Для общих расходов может не быть сотрудника
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses',
        verbose_name='Заказ'
    )
    category = models.CharField(
        'Категория',
        max_length=20,
        choices=ExpenseCategory.choices,
        default=ExpenseCategory.OTHER
    )
    amount = models.DecimalField(
        'Сумма',
        max_digits=10,
        decimal_places=2
    )
    description = models.TextField(
        'Описание',
        blank=True
    )
    photo = models.ImageField(
        'Фото чека',
        upload_to='expenses/',
        null=True,
        blank=True
    )
    expense_date = models.DateField(
        'Дата расхода',
        default=timezone.now
    )
    is_general = models.BooleanField(
        'Общий расход',
        default=False,
        help_text='Общие расходы компании (аренда, химия и т.д.)'
    )
    created_at = models.DateTimeField(
        'Дата создания',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Расход'
        verbose_name_plural = 'Расходы'
        ordering = ['-created_at']
    
    def __str__(self):
        if self.is_general:
            return f'ОБЩИЙ — {self.get_category_display()} ({self.amount} сом)'
        elif self.employee:
            return f'{self.employee.user.full_name} — {self.get_category_display()} ({self.amount} сом)'
        else:
            return f'Расход — {self.get_category_display()} ({self.amount} сом)'
