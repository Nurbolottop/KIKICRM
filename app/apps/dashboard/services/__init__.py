"""
Сервисный слой для Dashboard аналитики.
Содержит функции для сбора метрик и статистики.
"""
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Q, F
from django.utils import timezone


def get_main_metrics():
    """
    Возвращает основные метрики CRM.
    """
    from apps.clients.models import Client
    from apps.orders.models import Order, OrderStatus
    from apps.employees.models import Employee
    from apps.services.models import Service
    from apps.expenses.models import Expense, ExpenseStatus
    from apps.inventory.models import InventoryItem
    
    today = timezone.now().date()
    
    metrics = {
        'total_clients': Client.objects.count(),
        'total_orders': Order.objects.count(),
        'total_services': Service.objects.filter(is_active=True).count(),
        'total_employees': Employee.objects.filter(status='ACTIVE').count(),
        
        'active_orders': Order.objects.filter(
            status__in=[OrderStatus.ASSIGNED, OrderStatus.IN_PROGRESS]
        ).count(),
        
        'completed_orders': Order.objects.filter(
            status=OrderStatus.COMPLETED
        ).count(),
        
        'pending_expenses_count': Expense.objects.filter(
            status=ExpenseStatus.PENDING
        ).count(),
        
        'low_stock_items_count': InventoryItem.objects.filter(
            is_active=True,
            quantity__lte=F('min_quantity')
        ).count(),
    }
    
    return metrics


def get_today_metrics():
    """
    Возвращает метрики за сегодня.
    """
    from apps.clients.models import Client
    from apps.orders.models import Order, OrderStatus
    from apps.orders.models import OrderEmployee
    from apps.expenses.models import Expense
    
    today = timezone.now().date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end = timezone.make_aware(datetime.combine(today, datetime.max.time()))
    
    # Заказы на сегодня (по запланированной дате)
    orders_today = Order.objects.filter(
        scheduled_date=today
    ).count()
    
    # Завершенные сегодня (по статусу COMPLETED)
    completed_today = Order.objects.filter(
        status=OrderStatus.COMPLETED,
        updated_at__date=today
    ).count()
    
    # Расходы за сегодня
    expenses_today = Expense.objects.filter(
        created_at__range=(today_start, today_end)
    ).aggregate(
        total=Sum('amount'),
        count=Count('id')
    )
    
    # Активные клинеры сегодня (начали работу сегодня)
    active_cleaners_today = OrderEmployee.objects.filter(
        started_at__date=today
    ).values('employee').distinct().count()
    
    # Новые клиенты сегодня
    new_clients_today = Client.objects.filter(
        created_at__date=today
    ).count()
    
    return {
        'orders_today': orders_today,
        'completed_today': completed_today,
        'expenses_today_sum': expenses_today['total'] or 0,
        'expenses_today_count': expenses_today['count'] or 0,
        'active_cleaners_today': active_cleaners_today,
        'new_clients_today': new_clients_today,
    }


def get_financial_metrics():
    """
    Возвращает финансовые метрики.
    """
    from apps.orders.models import Order, OrderStatus
    from apps.expenses.models import Expense, ExpenseStatus
    
    # Сумма всех заказов
    orders_total = Order.objects.aggregate(
        total=Sum('price')
    )['total'] or 0
    
    # Сумма завершенных заказов
    completed_orders_total = Order.objects.filter(
        status=OrderStatus.COMPLETED
    ).aggregate(
        total=Sum('price')
    )['total'] or 0
    
    # Одобренные расходы
    approved_expenses = Expense.objects.filter(
        status=ExpenseStatus.APPROVED
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Ожидающие расходы
    pending_expenses = Expense.objects.filter(
        status=ExpenseStatus.PENDING
    ).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Оценочная валовая прибыль
    estimated_gross_profit = completed_orders_total - approved_expenses
    
    return {
        'orders_total_amount': orders_total,
        'completed_orders_amount': completed_orders_total,
        'approved_expenses_total': approved_expenses,
        'pending_expenses_total': pending_expenses,
        'estimated_gross_profit': estimated_gross_profit,
    }


def get_recent_orders(limit=5):
    """
    Возвращает последние заказы.
    """
    from apps.orders.models import Order
    return Order.objects.select_related(
        'client', 'service'
    ).order_by('-created_at')[:limit]


def get_recent_expenses(limit=5):
    """
    Возвращает последние расходы.
    """
    from apps.expenses.models import Expense
    return Expense.objects.select_related(
        'employee', 'order'
    ).order_by('-created_at')[:limit]


def get_low_stock_items():
    """
    Возвращает товары с низким остатком.
    """
    from apps.inventory.models import InventoryItem
    return InventoryItem.objects.filter(
        is_active=True,
        quantity__lte=F('min_quantity')
    ).select_related('category').order_by('quantity')[:10]


def get_active_orders_in_progress():
    """
    Возвращает заказы в работе с количеством назначенных сотрудников.
    """
    from apps.orders.models import Order, OrderStatus
    orders = Order.objects.filter(
        status__in=[OrderStatus.ASSIGNED, OrderStatus.IN_PROGRESS]
    ).select_related('client').annotate(
        employee_count=Count('order_employees', distinct=True)
    ).order_by('-scheduled_date')[:10]
    
    return orders


def get_cleaner_performance(limit=10):
    """
    Возвращает статистику работы клинеров.
    """
    from apps.users.models import UserRole
    from apps.employees.models import Employee
    from apps.orders.models import OrderEmployee
    
    # Получаем клинеров и их статистику
    cleaners = Employee.objects.filter(
        user__role__in=[UserRole.CLEANER, UserRole.SENIOR_CLEANER],
        status='ACTIVE'
    ).select_related('user')
    
    performance_data = []
    
    for cleaner in cleaners[:limit]:
        stats = OrderEmployee.objects.filter(
            employee=cleaner
        ).aggregate(
            assigned_count=Count('id'),
            confirmed_count=Count('id', filter=Q(is_confirmed=True)),
            started_count=Count('id', filter=Q(started_at__isnull=False)),
            finished_count=Count('id', filter=Q(finished_at__isnull=False))
        )
        
        performance_data.append({
            'employee': cleaner,
            'assigned_orders_count': stats['assigned_count'] or 0,
            'confirmed_orders_count': stats['confirmed_count'] or 0,
            'started_orders_count': stats['started_count'] or 0,
            'finished_orders_count': stats['finished_count'] or 0,
        })
    
    # Сортируем по количеству завершенных заказов
    performance_data.sort(
        key=lambda x: x['finished_orders_count'],
        reverse=True
    )
    
    return performance_data


def get_clients_by_source():
    """
    Возвращает распределение клиентов по источникам.
    """
    from apps.clients.models import Client
    sources_data = []
    
    for source_value, source_label in Client.ClientSource.choices:
        count = Client.objects.filter(source=source_value).count()
        sources_data.append({
            'source': source_label,
            'source_value': source_value,
            'count': count
        })
    
    return sources_data
