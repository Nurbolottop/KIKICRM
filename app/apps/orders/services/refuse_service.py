"""
Service layer для управления отказами клинеров.
"""
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count

from apps.orders.models import OrderEmployee, RefuseSettings


class RefuseService:
    """Сервис для проверки и управления отказами клинеров."""

    @staticmethod
    def can_refuse(employee):
        """
        Проверяет, может ли клинер отказаться от заказа.
        
        Args:
            employee: Employee instance
        
        Returns:
            bool: True если может отказаться, False если лимит исчерпан
        """
        settings = RefuseSettings.objects.filter(
            is_active=True
        ).first()

        if not settings:
            return True

        period = timezone.now() - timedelta(days=settings.period_days)

        refuses = OrderEmployee.objects.filter(
            employee=employee,
            refused_at__gte=period
        ).count()

        return refuses < settings.max_refuses

    @staticmethod
    def record_refuse(order_employee, reason=""):
        """
        Фиксирует отказ клинера.
        
        Args:
            order_employee: OrderEmployee instance
            reason: str, причина отказа
        """
        order_employee.refused_at = timezone.now()
        order_employee.refuse_reason = reason
        order_employee.save()

    @staticmethod
    def get_refuse_count(employee, days=None):
        """
        Получает количество отказов за период.
        
        Args:
            employee: Employee instance
            days: int, количество дней (если None, берется из настроек)
        
        Returns:
            int: количество отказов
        """
        settings = RefuseSettings.objects.filter(is_active=True).first()
        period_days = days or (settings.period_days if settings else 14)

        period = timezone.now() - timedelta(days=period_days)

        return OrderEmployee.objects.filter(
            employee=employee,
            refused_at__gte=period
        ).count()

    @staticmethod
    def get_problematic_cleaners(limit=5):
        """
        Получает список клинеров с наибольшим количеством отказов.
        
        Args:
            limit: int, максимальное количество клинеров
        
        Returns:
            list: список словарей с информацией о клинерах и их отказах
        """
        settings = RefuseSettings.objects.filter(
            is_active=True
        ).first()

        if not settings:
            return []

        period = timezone.now() - timedelta(days=settings.period_days)

        cleaners = (
            OrderEmployee.objects
            .filter(refused_at__gte=period)
            .values(
                "employee__id",
                "employee__user__first_name",
                "employee__user__last_name"
            )
            .annotate(refuses=Count("id"))
            .order_by("-refuses")[:limit]
        )

        return cleaners
