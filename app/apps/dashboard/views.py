from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from apps.accounts.models import UserRole
from .services.dashboard_service import (
    get_main_metrics,
    get_today_metrics,
    get_financial_metrics,
    get_financial_summary,
    get_recent_orders,
    get_recent_expenses,
    get_low_stock_items,
    get_active_orders_in_progress,
    get_cleaner_performance,
    get_clients_by_source,
    get_problematic_cleaners,
    get_orders_timeseries,
    get_revenue_timeseries,
    get_orders_by_status,
)


def has_full_dashboard_access(user):
    """Проверяет доступ к полному dashboard."""
    return user.role in [
        UserRole.FOUNDER,
        UserRole.MANAGER,
    ] or user.is_superuser


def has_limited_dashboard_access(user):
    """Проверяет доступ к ограниченному dashboard."""
    return user.role in [
        UserRole.OPERATOR,
        UserRole.SMM,
    ]


@login_required
def dashboard(request):
    """
    Dashboard view с аналитикой.
    Доступ:
    - Полный: FOUNDER, MANAGER
    - Ограниченный: OPERATOR, SMM
    - Редирект: остальные роли
    """
    user = request.user
    
    # Проверка доступа
    if user.role == UserRole.HR:
        return redirect('hr_dashboard')
    
    if not has_full_dashboard_access(user) and not has_limited_dashboard_access(user):
        # Для клинеров — редирект на панель клинера (index_cl)
        if user.role in [UserRole.CLEANER, UserRole.SENIOR_CLEANER]:
            return redirect('index_cl')
        # Для других ролей — показываем страницу с ошибкой
        messages.info(request, 'Доступ ограничен. Обратитесь к администратору.')
        return redirect('login')
    
    # Определяем режим доступа
    is_full_access = has_full_dashboard_access(user)
    
    # Собираем данные через service layer
    context = {
        'is_full_access': is_full_access,
        'user_role': user.role,
        'user_role_display': user.get_role_display(),
    }
    
    # Основные метрики (всем ролям)
    context['main_metrics'] = get_main_metrics()
    
    # Метрики за сегодня (всем ролям)
    context['today_metrics'] = get_today_metrics()
    
    # Последние заказы (всем ролям)
    context['recent_orders'] = get_recent_orders(limit=5)

    # Данные для графиков (всем ролям)
    context['chart_orders_ts'] = get_orders_timeseries(days=14)
    context['chart_revenue_ts'] = get_revenue_timeseries(days=14)
    context['chart_orders_status'] = get_orders_by_status()
    
    if is_full_access:
        # Полный доступ — все метрики
        context['financial_metrics'] = get_financial_metrics()
        context['financial_summary'] = get_financial_summary()
        context['recent_expenses'] = get_recent_expenses(limit=5)
        context['low_stock_items'] = get_low_stock_items()
        context['active_orders'] = get_active_orders_in_progress()
        context['cleaner_performance'] = get_cleaner_performance(limit=10)
        context['clients_by_source'] = get_clients_by_source()
        context['problematic_cleaners'] = get_problematic_cleaners()
    else:
        # Ограниченный доступ — только основные метрики
        context['financial_metrics'] = None
        context['financial_summary'] = None
        context['recent_expenses'] = None
        context['low_stock_items'] = None
        context['active_orders'] = None
        context['cleaner_performance'] = None
        context['clients_by_source'] = None
        context['problematic_cleaners'] = None
    
    return render(request, 'dashboard/index.html', context)
