from django.db import models
from django.conf import settings


class ReviewType(models.TextChoices):
    """Типы отзывов."""
    POSITIVE = 'POSITIVE', 'Положительный'
    NEGATIVE = 'NEGATIVE', 'Отрицательный'


class Review(models.Model):
    """Отзыв клиента о заказе."""

    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Заказ'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_reviews',
        verbose_name='Кто добавил'
    )
    review_type = models.CharField(
        'Тип отзыва',
        max_length=20,
        choices=ReviewType.choices,
        default=ReviewType.POSITIVE
    )
    description = models.TextField(
        'Описание',
        blank=True,
        default='',
        help_text='Текст отзыва или комментарий'
    )
    photo = models.ImageField(
        'Фото',
        upload_to='reviews/%Y/%m/',
        blank=True,
        null=True,
        help_text='Фотография к отзыву (скриншот, фото клиента и т.д.)'
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
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']

    def __str__(self):
        return f'Отзыв по заказу #{self.order.order_code} — {self.get_review_type_display()}'

    def get_type_badge_class(self):
        """Возвращает CSS класс для бейджа типа отзыва."""
        if self.review_type == ReviewType.POSITIVE:
            return 'success'
        return 'danger'
