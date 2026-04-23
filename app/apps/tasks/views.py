"""
Views для управления задачами чеклистов (Task Checklist System).
"""
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST

from apps.common.permissions import (
    can_assign_cleaners, can_view_cleaner_panel, can_assign_cleaner_tasks
)
from apps.employees.models import Employee
from .models import OrderTask, OrderTaskStatus
from .services import TaskChecklistService


@login_required
@require_POST
def assign_task_to_employee(request, task_id):
    """
    Назначить задачу сотруднику.
    Доступно: Manager, Senior Cleaner, Founder
    """
    if not (can_assign_cleaners(request.user) or can_assign_cleaner_tasks(request.user)):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Нет прав для назначения задач'})
        messages.error(request, 'Нет прав для назначения задач')
        return redirect('orders_list')
    
    task = get_object_or_404(OrderTask, id=task_id)
    employee_id = request.POST.get('employee_id')
    
    if not employee_id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Не выбран сотрудник'})
        messages.error(request, 'Не выбран сотрудник')
        return redirect('order_detail', pk=task.order.id)
    
    try:
        employee = Employee.objects.get(id=employee_id)
        TaskChecklistService.assign_task_to_employee(task, employee, request.user)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Задача назначена {employee.user.full_name}',
                'employee_name': employee.user.full_name
            })
        messages.success(request, f'Задача назначена {employee.user.full_name}')
        
    except Employee.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Сотрудник не найден'})
        messages.error(request, 'Сотрудник не найден')
    
    return redirect('order_detail', pk=task.order.id)


@login_required
@require_POST
def start_task(request, task_id):
    """
    Начать выполнение задачи.
    Доступно: Cleaner (свои задачи), Senior Cleaner, Manager, Founder
    """
    task = get_object_or_404(OrderTask, id=task_id)
    
    # Проверяем права на задачу
    can_start = False
    if request.user.is_superuser:
        can_start = True
    elif task.assigned_employees.filter(user=request.user).exists():
        can_start = True
    elif can_assign_cleaner_tasks(request.user):  # Senior Cleaner / Manager
        can_start = True
    
    if not can_start:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Нет прав для начала задачи'})
        messages.error(request, 'Нет прав для начала задачи')
        return redirect('cleaner_dashboard')
    
    TaskChecklistService.start_task(task, request.user)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Задача начата',
            'status': task.status,
            'status_label': task.get_status_display()
        })
    messages.success(request, 'Задача начата')
    return redirect('cleaner_dashboard')


@login_required
@require_POST
def complete_task(request, task_id):
    """
    Отметить задачу как выполненную.
    Доступно: Cleaner (свои задачи), Senior Cleaner, Manager, Founder
    """
    task = get_object_or_404(OrderTask, id=task_id)
    notes = request.POST.get('notes', '')
    
    # Проверяем права на задачу
    can_complete = False
    if request.user.is_superuser:
        can_complete = True
    elif task.assigned_employees.filter(user=request.user).exists():
        can_complete = True
    elif can_assign_cleaner_tasks(request.user):  # Senior Cleaner / Manager
        can_complete = True
    
    if not can_complete:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Нет прав для завершения задачи'})
        messages.error(request, 'Нет прав для завершения задачи')
        return redirect('cleaner_dashboard')
    
    # Сохраняем примечания если есть
    if notes:
        task.notes = notes
        task.save(update_fields=['notes'])
    
    TaskChecklistService.complete_task(task, request.user)
    
    # Проверяем, все ли задачи заказа выполнены
    stats = TaskChecklistService.get_order_task_stats(task.order)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response_data = {
            'success': True,
            'message': 'Задача выполнена',
            'status': task.status,
            'status_label': task.get_status_display(),
            'order_progress': stats['completion_percentage'],
            'is_fully_done': stats['is_fully_done']
        }
        if stats['is_fully_done']:
            response_data['message'] = 'Задача выполнена! Все задачи заказа завершены.'
        return JsonResponse(response_data)
    
    messages.success(request, 'Задача выполнена')
    return redirect('cleaner_dashboard')


@login_required
@require_POST
def skip_task(request, task_id):
    """
    Пропустить задачу.
    Доступно: Senior Cleaner, Manager, Founder
    """
    if not can_assign_cleaner_tasks(request.user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Нет прав для пропуска задачи'})
        messages.error(request, 'Нет прав для пропуска задачи')
        return redirect('order_detail', pk=task.order.id)
    
    task = get_object_or_404(OrderTask, id=task_id)
    TaskChecklistService.skip_task(task, request.user)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Задача пропущена',
            'status': task.status,
            'status_label': task.get_status_display()
        })
    messages.success(request, 'Задача пропущена')
    return redirect('order_detail', pk=task.order.id)


@login_required
@require_POST
def reset_task(request, task_id):
    """
    Сбросить задачу в начальное состояние.
    Доступно: Manager, Founder
    """
    from apps.common.permissions import can_edit_orders
    if not can_edit_orders(request.user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Нет прав для сброса задачи'})
        messages.error(request, 'Нет прав для сброса задачи')
        return redirect('order_detail', pk=task.order.id)
    
    task = get_object_or_404(OrderTask, id=task_id)
    TaskChecklistService.reset_task(task)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Задача сброшена',
            'status': task.status,
            'status_label': task.get_status_display()
        })
    messages.success(request, 'Задача сброшена')
    return redirect('order_detail', pk=task.order.id)


@login_required
def get_task_stats(request, order_id):
    """
    API для получения статистики задач заказа.
    """
    from apps.orders.models import Order
    
    order = get_object_or_404(Order, id=order_id)
    stats = TaskChecklistService.get_order_task_stats(order)
    
    return JsonResponse(stats)


@login_required
def my_tasks(request):
    """
    Список задач текущего пользователя (для Cleaner Panel).
    """
    if not can_view_cleaner_panel(request.user):
        messages.error(request, 'Нет доступа к панели клинера')
        return redirect('dashboard')
    
    try:
        employee = request.user.employee_profile
        tasks = TaskChecklistService.get_employee_tasks(employee)
    except Employee.DoesNotExist:
        tasks = []
    
    # Группируем задачи по заказам
    tasks_by_order = {}
    for task in tasks:
        order_id = task.order.id
        if order_id not in tasks_by_order:
            tasks_by_order[order_id] = {
                'order': task.order,
                'tasks': []
            }
        tasks_by_order[order_id]['tasks'].append(task)
    
    context = {
        'tasks_by_order': tasks_by_order,
        'total_tasks': len(tasks),
        'pending_tasks': len([t for t in tasks if t.status == OrderTaskStatus.PENDING]),
        'in_progress_tasks': len([t for t in tasks if t.status == OrderTaskStatus.IN_PROGRESS]),
        'done_tasks': len([t for t in tasks if t.status == OrderTaskStatus.DONE]),
    }
    
    return render(request, 'tasks/my_tasks.html', context)
