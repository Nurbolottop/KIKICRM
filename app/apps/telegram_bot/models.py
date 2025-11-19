from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core.cache import cache

class TelegramUser(models.Model):
    id_user = models.BigIntegerField(
        verbose_name="ID пользователя Telegram",
        unique=True
    )
    username = models.CharField(
        max_length=255,
        verbose_name="Имя пользователя",
        blank=True,
        null=True
    )
    first_name = models.CharField(
        max_length=255,
        verbose_name="Имя",
        blank=True,
        null=True
    )
    last_name = models.CharField(
        max_length=255,
        verbose_name="Фамилия",
        blank=True,
        null=True
    )
    chat_id = models.BigIntegerField(
        verbose_name="Чат ID"
    )
    # Связь с системным пользователем (клинером)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="telegram_account",
        verbose_name="Пользователь системы"
    )
    # Статус активности
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен"
    )
    # Последняя активность
    last_activity = models.DateTimeField(
        auto_now=True,
        verbose_name="Последняя активность"
    )
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата регистрации"
    )

    def __str__(self):
        if self.user:
            return f"{self.username} ({self.user.full_name})"
        return str(self.username)
    
    class Meta:
        verbose_name = "Telegram пользователь"
        verbose_name_plural = "Telegram пользователи"
