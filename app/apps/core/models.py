"""
Base models and mixins for the project.
"""
from django.db import models


class TimestampMixin(models.Model):
    """
    Abstract base model with created_at and updated_at timestamps.
    """
    created_at = models.DateTimeField(
        'Дата создания',
        auto_now_add=True
    )
    
    updated_at = models.DateTimeField(
        'Дата обновления',
        auto_now=True
    )

    class Meta:
        abstract = True
