from django.db import models
from django.conf import settings


class HRSettings(models.Model):
    """Настройки HR менеджера."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hr_settings',
        verbose_name='HR пользователь'
    )
    default_password = models.CharField(
        'Стандартный пароль',
        max_length=128,
        blank=True,
        default='',
        help_text='Пароль по умолчанию для новых клинеров'
    )

    class Meta:
        verbose_name = 'Настройки HR'
        verbose_name_plural = 'Настройки HR'

    def __str__(self):
        return f'HR настройки: {self.user}'
