"""
Сервисный слой для Dashboard аналитики.
Содержит функции для сбора метрик и статистики.
"""
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Q, F
from django.db.models.functions import TruncDate
from django.utils import timezone


def get_main_metrics():
    """
    Возвращает основные метрики CRM.
    """
    from apps.clients.models import Client
    from apps.orders.models import Order, OrderStatus
    from apps.employees.models import Employee
    from apps.services.models import Service
    from apps.expenses.models import Expense
    from apps.inventory.models import InventoryItem
    
    today = timezone.now().date()
    
    metrics = {
        'total_clients': Client.objects.count(),
        'total_orders': Order.objects.count(),
        'total_services': Service.objects.filter(is_active=True).count(),
        'total_employees': Employee.objects.filter(status='ACTIVE').count(),
        
        'active_orders': Order.objects.filter(
            status__in=[OrderStatus.PROCESSING, OrderStatus.IN_WORK, OrderStatus.ON_REVIEW]
        ).count(),
        
        'completed_orders': Order.objects.filter(
            status=OrderStatus.COMPLETED
        ).count(),
        
        'total_expenses_count': Expense.objects.count(),
        
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
    from apps.expenses.models import Expense
    
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
    
    # Все расходы
    total_expenses = Expense.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Оценочная валовая прибыль
    estimated_gross_profit = completed_orders_total - total_expenses
    
    return {
        'orders_total_amount': orders_total,
        'completed_orders_amount': completed_orders_total,
        'total_expenses': total_expenses,
        'estimated_gross_profit': estimated_gross_profit,
    }


def get_financial_summary():
    """
    Возвращает финансовую сводку за сегодня и месяц.
    """
    from apps.orders.models import Order, OrderStatus
    from apps.expenses.models import Expense
    
    today = timezone.now().date()
    month_start = today.replace(day=1)

    # Завершенные заказы (только COMPLETED считаются как доход)
    completed_orders = Order.objects.filter(
        status=OrderStatus.COMPLETED
    )

    # Заказы за сегодня
    orders_today = completed_orders.filter(
        updated_at__date=today
    )

    # Заказы за месяц
    orders_month = completed_orders.filter(
        updated_at__date__gte=month_start
    )

    # Все расходы за месяц
    expenses_month = Expense.objects.filter(
        created_at__date__gte=month_start
    )

    # Суммы
    orders_today_sum = orders_today.aggregate(
        total=Sum("price")
    )["total"] or 0

    orders_month_sum = orders_month.aggregate(
        total=Sum("price")
    )["total"] or 0

    expenses_month_sum = expenses_month.aggregate(
        total=Sum("amount")
    )["total"] or 0

    # Количество завершенных заказов за месяц
    completed_count = orders_month.count()

    # Средний чек
    avg_order = (
        orders_month_sum / completed_count
        if completed_count > 0
        else 0
    )

    # Прибыль
    profit = orders_month_sum - expenses_month_sum

    return {
        "orders_today_sum": orders_today_sum,
        "orders_month_sum": orders_month_sum,
        "expenses_month_sum": expenses_month_sum,
        "profit": profit,
        "avg_order": round(avg_order, 2),
    }


def get_recent_orders(limit=5):
    """
    Возвращает последние заказы.
    """
    from apps.orders.models import Order
    from apps.services.models import Service
    
    return Order.objects.select_related(
        'client', 'service'
    ).order_by('-created_at')[:limit]


def get_recent_expenses(limit=5):
    """
    Возвращает последние расходы.
    """
    from apps.expenses.models import Expense
    
    return Expense.objects.select_related(
        'user', 'order'
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
        status__in=[OrderStatus.PROCESSING, OrderStatus.IN_WORK, OrderStatus.ON_REVIEW]
    ).select_related('client').annotate(
        employee_count=Count('order_employees', distinct=True)
    ).order_by('-scheduled_date')[:10]
    
    return orders


def get_cleaner_performance(limit=10):
    """
    Возвращает статистику работы клинеров.
    """
    from apps.accounts.models import UserRole
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


def get_problematic_cleaners(limit=5):
    """
    Возвращает клинеров с наибольшим количеством отказов.
    """
    from apps.orders.models import RefuseSettings
    
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


def get_orders_timeseries(days=14):
    """Возвращает данные по заказам за последние N дней (кол-во по дням)."""
    from apps.orders.models import Order

    today = timezone.localdate()
    start_date = today - timedelta(days=days - 1)

    qs = (
        Order.objects.filter(created_at__date__gte=start_date)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )

    counts_by_day = {row['day']: row['count'] for row in qs}
    labels = []
    values = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        labels.append(d.strftime('%d.%m'))
        values.append(int(counts_by_day.get(d, 0)))

    return {
        'labels': labels,
        'values': values,
    }


def get_revenue_timeseries(days=14):
    """Возвращает доход (сумма price) завершенных заказов по дням за последние N дней."""
    from apps.orders.models import Order, OrderStatus

    today = timezone.localdate()
    start_date = today - timedelta(days=days - 1)

    qs = (
        Order.objects.filter(status=OrderStatus.COMPLETED, updated_at__date__gte=start_date)
        .annotate(day=TruncDate('updated_at'))
        .values('day')
        .annotate(total=Sum('price'))
        .order_by('day')
    )

    totals_by_day = {row['day']: float(row['total'] or 0) for row in qs}
    labels = []
    values = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        labels.append(d.strftime('%d.%m'))
        values.append(round(float(totals_by_day.get(d, 0)), 2))

    return {
        'labels': labels,
        'values': values,
    }


def get_orders_by_status():
    """Возвращает распределение заказов по статусам."""
    from apps.orders.models import Order, OrderStatus

    raw = Order.objects.values('status').annotate(count=Count('id')).order_by('-count')
    label_map = {value: label for value, label in OrderStatus.choices}

    labels = []
    values = []
    for row in raw:
        status = row['status']
        labels.append(label_map.get(status, status))
        values.append(int(row['count']))

    return {
        'labels': labels,
        'values': values,
    }
