"""Cleaner panel views - новая версия."""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from apps.orders.models import Order, OrderEmployee
from apps.accounts.models import UserRole


def is_cleaner(user):
    """Проверка что пользователь клинер."""
    return user.is_authenticated and user.role in [UserRole.CLEANER, UserRole.SENIOR_CLEANER]


@login_required
def index_cl(request):
    """Главная страница для клинеров."""
    if not is_cleaner(request.user):
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Эта страница только для клинеров.'
        })
    
    employee = request.user.employee if hasattr(request.user, 'employee') else None
    today = timezone.now().date()
    
    if employee:
        today_orders = OrderEmployee.objects.filter(
            employee=employee, order__scheduled_date=today
        ).select_related('order', 'order__client', 'order__service')[:10]
        all_orders = OrderEmployee.objects.filter(
            employee=employee
        ).select_related('order', 'order__client', 'order__service').order_by('-order__scheduled_date')[:20]
    else:
        today_orders = []
        all_orders = []
    
    return render(request, 'cleaner_panel/index_cl.html', {
        'employee': employee,
        'today_orders': today_orders,
        'all_orders': all_orders,
        'today': today,
        'is_senior': request.user.role == UserRole.SENIOR_CLEANER,
    })
    if not employee:
        # Показываем страницу ошибки вместо редиректа (избегаем цикла)
        return render(request, 'cleaner_panel/error.html', {
            'title': 'Профиль не найден',
            'message': 'Профиль сотрудника не найден. Обратитесь к менеджеру.',
        })
    
    today = timezone.now().date()
    
    # Orders for today
    today_orders = OrderEmployee.objects.filter(
        employee=employee,
        order__scheduled_date=today
    ).select_related('order', 'order__client', 'order__service')
    
    # Active orders (confirmed but not finished)
    active_orders = OrderEmployee.objects.filter(
        employee=employee,
        is_confirmed=True,
        finished_at__isnull=True
    ).select_related('order', 'order__client', 'order__service')
    
    # Stats
    total_completed = OrderEmployee.objects.filter(
        employee=employee,
        finished_at__isnull=False
    ).count()
    
    recent_orders = OrderEmployee.objects.filter(
        employee=employee
    ).select_related('order', 'order__client').order_by('-assigned_at')[:5]
    
    context = {
        'today_orders': today_orders,
        'active_orders': active_orders,
        'total_completed': total_completed,
        'recent_orders': recent_orders,
        'today': today,
    }
    return render(request, 'cleaner_panel/dashboard.html', context)


@login_required
def cleaner_orders_list(request):
    """List of orders for current employee."""
    if not is_cleaner_role(request.user):
        messages.error(request, 'У вас нет доступа.')
        return redirect('dashboard')
    
    employee = get_employee(request.user)
    if not employee:
        messages.error(request, 'Профиль сотрудника не найден.')
        return redirect('dashboard')
    
    # Get filter params
    status = request.GET.get('status', '')
    date = request.GET.get('date', '')
    
    order_employees = OrderEmployee.objects.filter(
        employee=employee
    ).select_related('order', 'order__client', 'order__service')
    
    # Apply filters
    if status:
        order_employees = order_employees.filter(order__status=status)
    if date:
        order_employees = order_employees.filter(order__scheduled_date=date)
    
    order_employees = order_employees.order_by('-order__scheduled_date', '-order__scheduled_time')
    
    context = {
        'order_employees': order_employees,
        'status_choices': OrderStatus.choices,
        'filter_status': status,
        'filter_date': date,
        'today': timezone.now().date(),
    }
    return render(request, 'cleaner_panel/orders_list.html', context)


@login_required
def cleaner_order_detail(request, order_id):
    """Detail view for cleaner order."""
    if not is_cleaner_role(request.user):
        messages.error(request, 'У вас нет доступа.')
        return redirect('dashboard')
    
    employee = get_employee(request.user)
    if not employee:
        messages.error(request, 'Профиль сотрудника не найден.')
        return redirect('dashboard')
    
    order_employee = get_object_or_404(
        OrderEmployee,
        order_id=order_id,
        employee=employee
    )
    
    order = order_employee.order
    photos = order.photos.filter(uploaded_by=employee).order_by('-uploaded_at')
    
    # Determine available actions
    can_confirm = not order_employee.is_confirmed
    can_start = order_employee.is_confirmed and not order_employee.started_at
    can_finish = order_employee.started_at and not order_employee.finished_at
    
    context = {
        'order_employee': order_employee,
        'order': order,
        'photos': photos,
        'can_confirm': can_confirm,
        'can_start': can_start,
        'can_finish': can_finish,
        'today': timezone.now().date(),
    }
    return render(request, 'cleaner_panel/order_detail.html', context)


@login_required
@require_POST
def confirm_assignment(request, order_id):
    """Confirm assignment for order."""
    if not is_cleaner_role(request.user):
        messages.error(request, 'У вас нет доступа.')
        return redirect('dashboard')
    
    employee = get_employee(request.user)
    if not employee:
        messages.error(request, 'Профиль сотрудника не найден.')
        return redirect('dashboard')
    
    order_employee = get_object_or_404(
        OrderEmployee,
        order_id=order_id,
        employee=employee
    )
    
    if order_employee.is_confirmed:
        messages.info(request, 'Вы уже подтвердили участие.')
    else:
        order_employee.is_confirmed = True
        order_employee.confirmed_at = timezone.now()
        order_employee.save()
        
        # Update order status if needed
        order = order_employee.order
        if order.status in [OrderStatus.NEW, OrderStatus.CONFIRMED]:
            order.status = OrderStatus.ASSIGNED
            order.save()
        
        # Telegram notification
        try:
            from apps.telegram_bot.services.telegram_service import notify_cleaner_confirmed
            notify_cleaner_confirmed(order_employee)
        except Exception:
            pass
        
        messages.success(request, 'Участие в заказе подтверждено!')
    
    return redirect('cleaner_order_detail', order_id=order_id)


@login_required
@require_POST
def start_work(request, order_id):
    """Start work on order."""
    if not is_cleaner_role(request.user):
        messages.error(request, 'У вас нет доступа.')
        return redirect('dashboard')
    
    employee = get_employee(request.user)
    if not employee:
        messages.error(request, 'Профиль сотрудника не найден.')
        return redirect('dashboard')
    
    order_employee = get_object_or_404(
        OrderEmployee,
        order_id=order_id,
        employee=employee
    )
    
    if not order_employee.is_confirmed:
        messages.error(request, 'Сначала подтвердите участие в заказе.')
        return redirect('cleaner_order_detail', order_id=order_id)
    
    if order_employee.started_at:
        messages.info(request, 'Работа уже начата.')
    else:
        order_employee.started_at = timezone.now()
        order_employee.save()
        
        # Update order status
        order = order_employee.order
        order.status = OrderStatus.IN_PROGRESS
        order.save()
        
        # Telegram notification
        try:
            from apps.telegram_bot.services.telegram_service import notify_work_started
            notify_work_started(order_employee)
        except Exception:
            pass
        
        messages.success(request, 'Работа начата!')
    
    return redirect('cleaner_order_detail', order_id=order_id)


@login_required
@require_POST
def finish_work(request, order_id):
    """Finish work on order."""
    if not is_cleaner_role(request.user):
        messages.error(request, 'У вас нет доступа.')
        return redirect('dashboard')
    
    employee = get_employee(request.user)
    if not employee:
        messages.error(request, 'Профиль сотрудника не найден.')
        return redirect('dashboard')
    
    order_employee = get_object_or_404(
        OrderEmployee,
        order_id=order_id,
        employee=employee
    )
    
    if not order_employee.started_at:
        messages.error(request, 'Сначала начните работу.')
        return redirect('cleaner_order_detail', order_id=order_id)
    
    if order_employee.finished_at:
        messages.info(request, 'Работа уже завершена.')
    else:
        order_employee.finished_at = timezone.now()
        order_employee.save()
        
        # Check if all employees finished
        order = order_employee.order
        all_finished = not OrderEmployee.objects.filter(
            order=order,
            finished_at__isnull=True
        ).exists()
        
        if all_finished:
            order.status = OrderStatus.COMPLETED
            order.save()
        
        # Telegram notification
        try:
            from apps.telegram_bot.services.telegram_service import notify_work_finished
            notify_work_finished(order_employee)
        except Exception:
            pass
        
        messages.success(request, 'Работа завершена!')
    
    return redirect('cleaner_order_detail', order_id=order_id)


@login_required
def upload_photo(request, order_id):
    """Upload photo for order."""
    if not is_cleaner_role(request.user):
        messages.error(request, 'У вас нет доступа.')
        return redirect('dashboard')
    
    employee = get_employee(request.user)
    if not employee:
        messages.error(request, 'Профиль сотрудника не найден.')
        return redirect('dashboard')
    
    order_employee = get_object_or_404(
        OrderEmployee,
        order_id=order_id,
        employee=employee
    )
    
    order = order_employee.order
    
    if request.method == 'POST':
        form = OrderPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            photo = form.save(commit=False)
            photo.order = order
            photo.uploaded_by = employee
            photo.save()
            messages.success(request, 'Фото загружено!')
            return redirect('cleaner_order_detail', order_id=order_id)
    else:
        form = OrderPhotoForm()
    
    context = {
        'order': order,
        'order_employee': order_employee,
        'form': form,
    }
    return render(request, 'cleaner_panel/upload_photo.html', context)


@login_required
@require_POST
def refuse_order(request, order_id):
    """Отказаться от заказа с проверкой лимита отказов."""
    if not is_cleaner_role(request.user):
        return JsonResponse({'error': 'Нет доступа'})
    
    employee = get_employee(request.user)
    if not employee:
        return JsonResponse({'error': 'Сотрудник не найден'})
    
    # Проверяем лимит отказов
    if not RefuseService.can_refuse(employee):
        return JsonResponse({
            'error': 'Вы превысили лимит отказов. Обратитесь к менеджеру.'
        })
    
    order = get_object_or_404(Order, id=order_id)
    reason = request.POST.get('reason', '')
    
    # Находим назначение сотрудника на этот заказ
    order_employee = OrderEmployee.objects.filter(
        order=order,
        employee=employee
    ).first()
    
    if not order_employee:
        return JsonResponse({'error': 'Вы не назначены на этот заказ'})
    
    # Фиксируем отказ
    RefuseService.record_refuse(order_employee, reason)
    
    # Удаляем назначение (освобождаем заказ)
    order_employee.delete()
    
    messages.success(request, 'Вы отказались от заказа')
    return JsonResponse({'success': True, 'message': 'Отказ зафиксирован'})
