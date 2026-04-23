"""Cleaner panel views - новая версия."""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Count, Q, Sum

from apps.orders.models import Order, OrderEmployee
from apps.accounts.models import UserRole
from apps.tasks.models import OrderTask, OrderTaskStatus
from apps.orders.services.order_status_service import OrderStatusService
from apps.employees.models import EmployeeEarning


def _notify_order_event(order: Order, status_name: str, user, old_status: str = None) -> None:
    try:
        OrderStatusService._send_status_notification(order, status_name, user, old_status)
    except Exception:
        return


def is_cleaner(user):
    """Проверка что пользователь клинер."""
    return user.is_authenticated and user.role in [UserRole.CLEANER, UserRole.SENIOR_CLEANER]


def _get_employee(request):
    return request.user.employee if hasattr(request.user, 'employee') else None


def _is_senior(user):
    return user.is_authenticated and user.role == UserRole.SENIOR_CLEANER


def _is_senior_on_order(order: Order, employee) -> bool:
    if not employee:
        return False
    return OrderEmployee.objects.filter(
        order=order,
        employee=employee,
        role_on_order='senior_cleaner',
    ).exists()


def _get_assigned_employees_qs(order: Order):
    return OrderEmployee.objects.filter(order=order).select_related('employee', 'employee__user')


def _is_work_started(order: Order) -> bool:
    return order.senior_cleaner_status in [
        Order.SeniorCleanerStatus.WORKING,
        Order.SeniorCleanerStatus.SENT_FOR_REVIEW,
    ]


def _ensure_order_tasks_from_service_checklist(order: Order) -> None:
    """Создает OrderTask из service.checklist, если задач у заказа еще нет."""
    # Если уже есть основные задачи (не доп. задачи менеджера) — не создаем повторно
    if order.tasks.filter(order_position__lt=100000).exists():
        return
    if not order.service or not order.service.checklist:
        return

    checklist = order.service.checklist
    pos = 1

    # Поддерживаем оба формата:
    # 1) [{'name': 'Кухня', 'tasks': ['...', ...]}, ...]
    # 2) ['Задача 1', 'Задача 2']
    if isinstance(checklist, list) and checklist and isinstance(checklist[0], dict):
        for room in checklist:
            room_name = (room or {}).get('name')
            tasks = (room or {}).get('tasks') or []
            for title in tasks:
                title = (title or '').strip()
                if not title:
                    continue
                description = f"Комната: {room_name}" if room_name else ''
                OrderTask.objects.create(
                    order=order,
                    title=title,
                    description=description,
                    order_position=pos,
                    status=OrderTaskStatus.PENDING,
                )
                pos += 1
        return

    if isinstance(checklist, list):
        for title in checklist:
            title = (title or '').strip()
            if not title:
                continue
            OrderTask.objects.create(
                order=order,
                title=title,
                description='',
                order_position=pos,
                status=OrderTaskStatus.PENDING,
            )
            pos += 1


@login_required
def profile_cl(request):
    """Страница профиля клинера."""
    if not is_cleaner(request.user):
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Эта страница только для клинеров.'
        })
    
    employee = _get_employee(request)
    today = timezone.now().date()
    
    # Статистика
    if employee:
        total_orders = OrderEmployee.objects.filter(employee=employee).count()
        completed_orders = OrderEmployee.objects.filter(
            employee=employee, 
            finished_at__isnull=False
        ).count()
        today_orders_count = OrderEmployee.objects.filter(
            employee=employee,
            order__scheduled_date=today
        ).count()
    else:
        total_orders = 0
        completed_orders = 0
        today_orders_count = 0

    earnings_total = 0
    earnings_month_due = 0
    if employee:
        earnings_total = EmployeeEarning.objects.filter(employee=employee).aggregate(
            total=Sum('amount')
        )['total'] or 0

        earnings_month_due = EmployeeEarning.objects.filter(
            employee=employee,
            is_paid=False,
            earned_at__date__gte=today.replace(day=1)
        ).aggregate(total=Sum('amount'))['total'] or 0
    
    return render(request, 'cleaner_panel/profile_cl.html', {
        'employee': employee,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'today_orders_count': today_orders_count,
        'is_senior': request.user.role == UserRole.SENIOR_CLEANER,
        'earnings_total': earnings_total,
        'earnings_month_due': earnings_month_due,
    })


@login_required
def profile_edit_cl(request):
    """Редактирование профиля клинера."""
    if not is_cleaner(request.user):
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Эта страница только для клинеров.'
        })

    employee = _get_employee(request)
    if request.method == 'POST':
        full_name = (request.POST.get('full_name') or '').strip()
        phone_secondary = (request.POST.get('phone_secondary') or '').strip()
        avatar = request.FILES.get('avatar')

        request.user.full_name = full_name
        request.user.save(update_fields=['full_name'])

        if employee is not None:
            employee.phone_secondary = phone_secondary
            if avatar:
                employee.avatar = avatar
                employee.save(update_fields=['phone_secondary', 'avatar'])
            else:
                employee.save(update_fields=['phone_secondary'])

        return redirect('profile_cl')

    return render(request, 'cleaner_panel/profile_edit_cl.html', {
        'employee': employee,
        'is_senior': request.user.role == UserRole.SENIOR_CLEANER,
    })


@login_required
def orders_cl(request):
    """Страница списка заказов клинера."""
    if not is_cleaner(request.user):
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Эта страница только для клинеров.'
        })
    
    employee = _get_employee(request)
    
    # Только заказы на которые назначен клинер
    if employee:
        from apps.orders.models import OrderStatus
        orders_qs = OrderEmployee.objects.filter(
            employee=employee
        ).select_related('order', 'order__client', 'order__service')
        
        # Фильтр по типу (актуальные/успешные/отмененные)
        list_type = (request.GET.get('type') or 'active').strip().lower()
        if list_type not in ('active', 'success', 'canceled'):
            list_type = 'active'
        
        if list_type == 'success':
            orders_qs = orders_qs.filter(order__status=OrderStatus.COMPLETED)
        elif list_type == 'canceled':
            orders_qs = orders_qs.filter(order__status=OrderStatus.CANCELLED)
        else:
            orders_qs = orders_qs.exclude(order__status__in=[OrderStatus.COMPLETED, OrderStatus.CANCELLED])
        
        orders = orders_qs.order_by('-order__scheduled_date', '-order__scheduled_time')
    else:
        orders = []
        list_type = 'active'
    
    return render(request, 'cleaner_panel/orders_cl.html', {
        'orders': orders,
        'employee': employee,
        'is_senior': request.user.role == UserRole.SENIOR_CLEANER,
        'type_filter': list_type,
    })


@login_required
def order_detail_cl(request, order_id):
    """Детали заказа для клинера."""
    if not is_cleaner(request.user):
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Эта страница только для клинеров.'
        })
    
    order = get_object_or_404(Order, id=order_id)
    employee = _get_employee(request)
    
    # Проверяем что клинер назначен на этот заказ
    if employee:
        order_employee = OrderEmployee.objects.filter(
            order=order, 
            employee=employee
        ).first()
        
        if not order_employee:
            return render(request, 'cleaner_panel/error_cl.html', {
                'message': 'Вы не назначены на этот заказ.'
            })
    else:
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Профиль сотрудника не найден.'
        })
    
    _ensure_order_tasks_from_service_checklist(order)

    all_assigned_cleaners = _get_assigned_employees_qs(order)
    assigned_employees = [oe.employee for oe in all_assigned_cleaners if oe.employee]

    all_tasks = order.tasks.prefetch_related('assigned_employees', 'assigned_employees__user').order_by('order_position', 'id')
    extra_tasks = all_tasks.filter(order_position__gte=100000)
    main_tasks = all_tasks.filter(order_position__lt=100000)

    # Группируем по комнате из description "Комната: ..."
    grouped = {}
    for t in main_tasks:
        room = ''
        if t.description and t.description.startswith('Комната:'):
            room = t.description.replace('Комната:', '', 1).strip()
        grouped.setdefault(room or 'Без комнаты', []).append(t)

    can_assign = False # _is_senior(request.user) and _is_senior_on_order(order, employee)
    can_review = _is_senior(request.user) and _is_senior_on_order(order, employee)
    work_started = _is_work_started(order)
    all_assigned = main_tasks.exists() and main_tasks.filter(assigned_employees__isnull=True).count() == 0

    # Для таймера берем started_at и finished_at у назначения senior_cleaner
    senior_assignment = OrderEmployee.objects.filter(
        order=order,
        role_on_order='senior_cleaner',
    ).select_related('employee').first()
    work_started_at = senior_assignment.started_at if senior_assignment else None
    work_finished_at = senior_assignment.finished_at if senior_assignment else None
    
    return render(request, 'cleaner_panel/order_detail_cl.html', {
        'order': order,
        'order_employee': order_employee,
        'employee': employee,
        'is_senior': request.user.role == UserRole.SENIOR_CLEANER,
        'all_assigned_cleaners': all_assigned_cleaners,
        'task_groups': grouped,
        'extra_tasks': extra_tasks,
        'assigned_employees': assigned_employees,
        'can_assign': can_assign,
        'can_review': can_review,
        'work_started': work_started,
        'work_started_at': work_started_at,
        'work_finished_at': work_finished_at,
        'all_tasks_assigned': all_assigned,
    })


@login_required
@require_POST
def assign_task_cl(request, order_id, task_id):
    """Больше не используется — распределяет менеджер."""
    return JsonResponse({'ok': False, 'error': 'Старший клинер больше не распределяет задачи. Это делает менеджер.'}, status=403)


@login_required
@require_POST
def update_task_deadline_cl(request, order_id, task_id):
    if not is_cleaner(request.user):
        return redirect('dashboard')

    order = get_object_or_404(Order, id=order_id)
    employee = _get_employee(request)
    if not _is_senior(request.user) or not _is_senior_on_order(order, employee):
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Только старший клинер может менять дедлайны задач.'
        })

    task = get_object_or_404(OrderTask, id=task_id, order=order)
    raw = (request.POST.get('deadline') or '').strip()

    if not raw:
        old = task.deadline
        task.deadline = None
        task.save(update_fields=['deadline'])
        if old:
            _notify_order_event(order, f"⏱️ Дедлайн снят: {task.title}", request.user)
        return redirect('order_detail_cl', order_id=order.id)

    try:
        dt = timezone.datetime.fromisoformat(raw)
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt, timezone.get_current_timezone())
    except Exception:
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Некорректный формат дедлайна.'
        })

    task.deadline = dt
    task.save(update_fields=['deadline'])
    _notify_order_event(order, f"⏱️ Дедлайн обновлён: {task.title}", request.user)
    return redirect('order_detail_cl', order_id=order.id)


@login_required
@require_POST
def senior_done_cl(request, order_id):
    if not is_cleaner(request.user):
        return redirect('dashboard')

    order = get_object_or_404(Order, id=order_id)
    employee = _get_employee(request)
    if not employee or not _is_senior(request.user) or not _is_senior_on_order(order, employee):
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Только старший клинер может завершить заказ.'
        })

    not_done_exists = order.tasks.exclude(status=OrderTaskStatus.DONE).exists()
    if not_done_exists:
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Нельзя завершить заказ — есть невыполненные/непринятые задачи.'
        })

    senior_assignment = OrderEmployee.objects.filter(
        order=order,
        role_on_order='senior_cleaner',
        employee=employee,
    ).first()
    if senior_assignment and not senior_assignment.finished_at:
        senior_assignment.finished_at = timezone.now()
        senior_assignment.save(update_fields=['finished_at'])

    if order.senior_cleaner_status == Order.SeniorCleanerStatus.SENT_FOR_REVIEW:
        return redirect('order_detail_cl', order_id=order.id)

    if order.senior_cleaner_status != Order.SeniorCleanerStatus.WORKING:
        order.senior_cleaner_status = Order.SeniorCleanerStatus.WORKING
        order.save(update_fields=['senior_cleaner_status'])

    OrderStatusService.senior_send_for_review(order, request.user)

    # Детальное уведомление в Telegram (тема «Уведомления»)
    try:
        from apps.notifications.services.telegram_service import TelegramService
        now_str = timezone.now().strftime('%H:%M')
        sched_date = order.scheduled_date.strftime('%d.%m.%Y') if order.scheduled_date else '—'
        sched_time = order.scheduled_time.strftime('%H:%M') if order.scheduled_time else ''
        senior_name = getattr(request.user, 'full_name', '') or getattr(request.user, 'phone', str(request.user))
        text = (
            f"📋 <b>Заказ передан на проверку менеджеру</b>\n\n"
            f"📋 Заказ: <b>{order.order_code}</b>\n"
            f"🛁 Услуга: {order.service.name if order.service else '—'}\n"
            f"👤 Клиент: {order.client.get_full_name() if order.client else '—'}\n"
            f"📍 Адрес: {order.address or '—'}\n"
            f"📅 Дата: {sched_date} {sched_time}\n\n"
            f"⭐ Ст. клинер: {senior_name}\n"
            f"⏰ Передано в: {now_str}"
        )
        TelegramService().send_cleaner_message(text)
    except Exception:
        pass

    return redirect('order_detail_cl', order_id=order.id)


@login_required
@require_POST
def bulk_assign_tasks_cl(request, order_id):
    """Больше не используется — распределяет менеджер."""
    return JsonResponse({'ok': False, 'error': 'Старший клинер больше не распределяет задачи. Это делает менеджер.'}, status=403)


@login_required
@require_POST
def start_work_cl(request, order_id):
    if not is_cleaner(request.user):
        return redirect('dashboard')

    order = get_object_or_404(Order, id=order_id)
    employee = _get_employee(request)
    if not _is_senior(request.user) or not _is_senior_on_order(order, employee):
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Только старший клинер может начать работу.'
        })

    if _is_work_started(order):
        return redirect('order_detail_cl', order_id=order.id)

    main_tasks = order.tasks.filter(order_position__lt=100000)
    if main_tasks.exists() and main_tasks.filter(assigned_employees__isnull=True).exists():
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Сначала распределите все задачи.'
        })

    # Ставим статус заказа и фиксируем время старта на назначении старшего клинера
    old_status = order.senior_cleaner_status
    order.senior_cleaner_status = Order.SeniorCleanerStatus.WORKING
    order.save(update_fields=['senior_cleaner_status'])

    senior_assignment, _ = OrderEmployee.objects.get_or_create(
        order=order,
        employee=employee,
        defaults={'role_on_order': 'senior_cleaner'},
    )
    if not senior_assignment.started_at:
        senior_assignment.started_at = timezone.now()
        senior_assignment.save(update_fields=['started_at'])

    # Переводим задачи в работу
    now = timezone.now()
    for t in order.tasks.filter(status=OrderTaskStatus.PENDING):
        t.status = OrderTaskStatus.IN_PROGRESS
        t.started_at = now
        t.save(update_fields=['status', 'started_at'])

    _notify_order_event(order, "🧹 Старт работ (клинеры)", request.user, old_status)

    # Детальное уведомление в Telegram (тема «Уведомления»)
    try:
        from apps.notifications.services.telegram_service import TelegramService
        cleaner_oes = order.order_employees.filter(role_on_order='cleaner').select_related('employee__user')
        cleaner_names = ', '.join(
            oe.employee.user.full_name for oe in cleaner_oes if oe.employee and oe.employee.user
        ) or '—'
        now_str = timezone.now().strftime('%H:%M')
        sched_date = order.scheduled_date.strftime('%d.%m.%Y') if order.scheduled_date else '—'
        sched_time = order.scheduled_time.strftime('%H:%M') if order.scheduled_time else ''
        senior_name = getattr(request.user, 'full_name', '') or getattr(request.user, 'phone', str(request.user))
        text = (
            f"▶️ <b>Старт работ</b>\n\n"
            f"📋 Заказ: <b>{order.order_code}</b>\n"
            f"🛁 Услуга: {order.service.name if order.service else '—'}\n"
            f"👤 Клиент: {order.client.get_full_name() if order.client else '—'}\n"
            f"📍 Адрес: {order.address or '—'}\n"
            f"📅 Дата: {sched_date} {sched_time}\n\n"
            f"⭐ Ст. клинер: {senior_name}\n"
            f"👥 Клинеры: {cleaner_names}\n"
            f"⏰ Начало: {now_str}"
        )
        TelegramService().send_cleaner_message(text)
    except Exception:
        pass

    return redirect('order_detail_cl', order_id=order.id)


@login_required
@require_POST
def complete_task_cl(request, order_id, task_id):
    if not is_cleaner(request.user):
        return redirect('dashboard')

    order = get_object_or_404(Order, id=order_id)
    employee = _get_employee(request)
    task = get_object_or_404(OrderTask, id=task_id, order=order)

    if not employee or not task.assigned_employees.filter(id=employee.id).exists():
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Вы можете отмечать только свои задачи.'
        })

    # Если задачу выполнил старший клинер, она сразу принимается (некому проверять)
    # Если обычный клинер — отправляется на проверку старшему
    is_senior_on_this_order = _is_senior(request.user) and _is_senior_on_order(order, employee)
    
    if is_senior_on_this_order:
        task.status = OrderTaskStatus.DONE
    else:
        task.status = OrderTaskStatus.ON_REVIEW
    
    task.finished_at = timezone.now()
    task.finished_by = request.user
    task.save(update_fields=['status', 'finished_at', 'finished_by'])
    return redirect('order_detail_cl', order_id=order.id)


@login_required
@require_POST
def accept_task_cl(request, order_id, task_id):
    if not is_cleaner(request.user):
        return redirect('dashboard')

    order = get_object_or_404(Order, id=order_id)
    employee = _get_employee(request)
    if not _is_senior(request.user) or not _is_senior_on_order(order, employee):
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Только старший клинер может принимать задачи.'
        })

    task = get_object_or_404(OrderTask, id=task_id, order=order)
    if task.status != OrderTaskStatus.ON_REVIEW:
        return redirect('order_detail_cl', order_id=order.id)

    task.status = OrderTaskStatus.DONE
    task.save(update_fields=['status'])
    _notify_order_event(order, f"☑️ Принята задача: {task.title}", request.user)
    from django.urls import reverse
    return redirect(reverse('order_detail_cl', kwargs={'order_id': order.id}) + f'#task-{task_id}')


@login_required
@require_POST
def rework_task_cl(request, order_id, task_id):
    if not is_cleaner(request.user):
        return redirect('dashboard')

    order = get_object_or_404(Order, id=order_id)
    employee = _get_employee(request)
    if not _is_senior(request.user) or not _is_senior_on_order(order, employee):
        return render(request, 'cleaner_panel/error_cl.html', {
            'message': 'Только старший клинер может отправлять задачи на переделку.'
        })

    task = get_object_or_404(OrderTask, id=task_id, order=order)
    if task.status != OrderTaskStatus.ON_REVIEW:
        return redirect('order_detail_cl', order_id=order.id)

    task.status = OrderTaskStatus.IN_PROGRESS
    task.finished_at = None
    task.finished_by = None
    task.save(update_fields=['status', 'finished_at', 'finished_by'])
    _notify_order_event(order, f"🔁 Переделка: {task.title}", request.user)
    from django.urls import reverse
    return redirect(reverse('order_detail_cl', kwargs={'order_id': order.id}) + f'#task-{task_id}')
