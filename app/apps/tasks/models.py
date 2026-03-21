"""
Модели чеклистов задач для уборки (Task Checklist System).

Шаблоны задач (ChecklistTemplate) привязаны к услугам.
При создании заказа автоматически генерируются OrderTask из шаблона.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone

from apps.services.models import Service
from apps.orders.models import Order
from apps.employees.models import Employee


class ChecklistTemplate(models.Model):
    """Шаблон чеклиста для услуги."""
    
    service = models.OneToOneField(
        Service,
        on_delete=models.CASCADE,
        related_name='checklist_template',
        verbose_name='Услуга'
    )
    name = models.CharField(
        'Название',
        max_length=255,
        help_text='Например: Стандартный чеклист для генеральной уборки'
    )
    description = models.TextField(
        'Описание',
        blank=True,
        help_text='Дополнительное описание шаблона'
    )
    is_active = models.BooleanField(
        'Активен',
        default=True
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
        verbose_name = 'Шаблон чеклиста'
        verbose_name_plural = 'Шаблоны чеклистов'
        ordering = ['name']
    
    def __str__(self):
        return f'{self.name} ({self.service.name})'


class ChecklistTemplateTask(models.Model):
    """Задача в шаблоне чеклиста."""
    
    template = models.ForeignKey(
        ChecklistTemplate,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name='Шаблон'
    )
    title = models.CharField(
        'Название задачи',
        max_length=255,
        help_text='Например: Протереть пыль, Помыть пол'
    )
    description = models.TextField(
        'Описание',
        blank=True,
        help_text='Детальное описание что нужно сделать'
    )
    order = models.PositiveIntegerField(
        'Порядок',
        default=0,
        help_text='Порядок отображения задач'
    )
    is_active = models.BooleanField(
        'Активна',
        default=True
    )
    created_at = models.DateTimeField(
        'Дата создания',
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = 'Задача в шаблоне'
        verbose_name_plural = 'Задачи в шаблоне'
        ordering = ['order', 'id']
    
    def __str__(self):
        return f'{self.title} ({self.template.name})'


class OrderTaskStatus(models.TextChoices):
    """Статусы выполнения задачи заказа."""
    PENDING = 'PENDING', 'Ожидает'
    IN_PROGRESS = 'IN_PROGRESS', 'В работе'
    ON_REVIEW = 'ON_REVIEW', 'На проверке'
    DONE = 'DONE', 'Выполнено'
    SKIPPED = 'SKIPPED', 'Пропущено'


class OrderTask(models.Model):
    """Задача конкретного заказа (создается из шаблона)."""
    
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name='Заказ'
    )
    title = models.CharField(
        'Название задачи',
        max_length=255
    )
    description = models.TextField(
        'Описание',
        blank=True
    )
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=OrderTaskStatus.choices,
        default=OrderTaskStatus.PENDING
    )
    assigned_employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name='Назначенный сотрудник'
    )
    order_position = models.PositiveIntegerField(
        'Порядок',
        default=0
    )
    created_at = models.DateTimeField(
        'Дата создания',
        auto_now_add=True
    )
    started_at = models.DateTimeField(
        'Начато',
        null=True,
        blank=True
    )
    finished_at = models.DateTimeField(
        'Завершено',
        null=True,
        blank=True
    )
    deadline = models.DateTimeField(
        'Дедлайн',
        null=True,
        blank=True
    )
    finished_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='completed_tasks',
        verbose_name='Кто завершил'
    )
    notes = models.TextField(
        'Примечания',
        blank=True,
        help_text='Комментарии к выполнению задачи'
    )
    
    class Meta:
        verbose_name = 'Задача заказа'
        verbose_name_plural = 'Задачи заказа'
        ordering = ['order_position', 'id']
    
    def __str__(self):
        return f'{self.title} ({self.order.order_code})'
    
    def start(self, user=None):
        """Начать выполнение задачи."""
        if self.status == OrderTaskStatus.PENDING:
            self.status = OrderTaskStatus.IN_PROGRESS
            self.started_at = timezone.now()
            self.save(update_fields=['status', 'started_at'])
    
    def complete(self, user=None):
        """Отметить задачу как выполненную."""
        self.status = OrderTaskStatus.DONE
        self.finished_at = timezone.now()
        self.finished_by = user
        self.save(update_fields=['status', 'finished_at', 'finished_by'])
    
    def skip(self, user=None):
        """Пропустить задачу."""
        self.status = OrderTaskStatus.SKIPPED
        self.finished_at = timezone.now()
        self.finished_by = user
        self.save(update_fields=['status', 'finished_at', 'finished_by'])
    
    def reset(self):
        """Сбросить задачу в начальное состояние."""
        self.status = OrderTaskStatus.PENDING
        self.started_at = None
        self.finished_at = None
        self.finished_by = None
        self.save(update_fields=['status', 'started_at', 'finished_at', 'finished_by'])
    
    @property
    def is_done(self):
        return self.status == OrderTaskStatus.DONE
    
    @property
    def duration(self):
        """Время выполнения задачи в минутах."""
        if self.started_at and self.finished_at:
            delta = self.finished_at - self.started_at
            return int(delta.total_seconds() / 60)
        return None
