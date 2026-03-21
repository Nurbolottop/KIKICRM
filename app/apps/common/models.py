from django.db import models


class TimeStampedModel(models.Model):
    """Абстрактная модель с временными метками создания и обновления."""
    created_at = models.DateTimeField(
        'Дата создания',
        auto_now_add=True,
        db_index=True
    )
    updated_at = models.DateTimeField(
        'Дата обновления',
        auto_now=True
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']


class ActiveModel(models.Model):
    """Абстрактная модель с флагом активности."""
    is_active = models.BooleanField(
        'Активно',
        default=True,
        db_index=True
    )

    class Meta:
        abstract = True


class BaseModel(TimeStampedModel, ActiveModel):
    """Комбинированная абстрактная модель с временными метками и активностью."""

    class Meta:
        abstract = True
        ordering = ['-created_at']
