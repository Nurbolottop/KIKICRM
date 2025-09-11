from django.db import models
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
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата регистрации"
    )

    def __str__(self):
        return str(self.username)
