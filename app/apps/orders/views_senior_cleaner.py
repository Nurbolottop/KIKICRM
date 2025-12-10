"""Views для старшего клинера"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from apps.orders import models as orders_models


@login_required
def senior_cleaner_accept_order(request, pk):
    """Старший клинер принимает заказ"""
    order = get_object_or_404(orders_models.Order, pk=pk)
    
    if request.method == "POST":
        order.status_senior_cleaner = orders_models.Order.SeniorCleanerStatus.ACCEPTED
        order.save(update_fields=["status_senior_cleaner"])
        messages.success(request, f"Заказ {order.code} принят в работу")
    
    return redirect("orders:order_detail", pk=pk)


@login_required
def senior_cleaner_decline_order(request, pk):
    """Старший клинер отказывается от заказа"""
    order = get_object_or_404(orders_models.Order, pk=pk)
    
    if request.method == "POST":
        decline_reason = request.POST.get("decline_reason", "")
        order.status_senior_cleaner = orders_models.Order.SeniorCleanerStatus.DECLINED
        order.decline_reason = decline_reason
        order.save(update_fields=["status_senior_cleaner", "decline_reason"])
        messages.warning(request, f"Вы отказались от заказа {order.code}")
    
    return redirect("orders:order_detail", pk=pk)


@login_required
def senior_cleaner_start_work(request, pk):
    """Старший клинер начинает работу"""
    order = get_object_or_404(orders_models.Order, pk=pk)
    
    if request.method == "POST":
        order.status_senior_cleaner = orders_models.Order.SeniorCleanerStatus.IN_PROGRESS
        order.work_started_at = timezone.now()
        order.save(update_fields=["status_senior_cleaner", "work_started_at"])
        messages.success(request, f"Работа по заказу {order.code} начата")
    
    return redirect("orders:order_detail", pk=pk)


@login_required
def senior_cleaner_finish_work(request, pk):
    """Старший клинер завершает работу"""
    order = get_object_or_404(orders_models.Order, pk=pk)
    
    if request.method == "POST":
        comment = request.POST.get("senior_cleaner_comment", "")
        order.status_senior_cleaner = orders_models.Order.SeniorCleanerStatus.PENDING_REVIEW
        order.status_manager = orders_models.Order.ManagerStatus.PENDING_REVIEW  # Автоматически меняем статус менеджера
        order.work_finished_at = timezone.now()
        order.senior_cleaner_comment = comment
        order.save(update_fields=["status_senior_cleaner", "status_manager", "work_finished_at", "senior_cleaner_comment"])
        messages.success(request, f"Работа по заказу {order.code} завершена и отправлена на проверку менеджеру")
    
    return redirect("orders:order_detail", pk=pk)


@login_required
def task_assign_cleaner(request, pk):
    """Назначение клинера на задачу (старший клинер)"""
    task = get_object_or_404(orders_models.Task, pk=pk)
    
    if request.method == "POST":
        cleaner_id = request.POST.get("cleaner")
        if cleaner_id:
            task.cleaner_id = cleaner_id
            task.save(update_fields=["cleaner"])
            messages.success(request, f"Клинер назначен на задачу: {task.description}")
        else:
            task.cleaner = None
            task.save(update_fields=["cleaner"])
            messages.info(request, f"Клинер снят с задачи: {task.description}")
    
    return redirect("orders:order_detail", pk=task.order.pk)


@login_required
def task_submit_for_review(request, pk):
    """Клинер отправляет свою задачу на проверку"""
    task = get_object_or_404(orders_models.Task, pk=pk)
    order = task.order
    if request.method == "POST":
        # Разрешаем только исполнителю задачи или обычному клинеру, назначенному на неё
        if request.user.role == 'CLEANER' and task.cleaner_id == request.user.id:
            task.status = 'PENDING_REVIEW'
            task.save(update_fields=["status"])
            messages.success(request, f"Задача отправлена на проверку: {task.description}")
        else:
            messages.error(request, "Вы не можете отправить на проверку эту задачу")
    return redirect("orders:order_detail", pk=order.pk)


@login_required
def task_approve(request, pk):
    """Старший клинер принимает задачу как выполненную"""
    task = get_object_or_404(orders_models.Task, pk=pk)
    order = task.order
    if request.method == "POST":
        if request.user.role == 'SENIOR_CLEANER' and order.senior_cleaner_id == request.user.id:
            task.status = 'DONE'
            task.save(update_fields=["status"])
            messages.success(request, f"Задача принята: {task.description}")
        else:
            messages.error(request, "Вы не можете подтвердить эту задачу")
    return redirect("orders:order_detail", pk=order.pk)


@login_required
def task_return_to_work(request, pk):
    """Старший клинер возвращает задачу на доработку"""
    task = get_object_or_404(orders_models.Task, pk=pk)
    order = task.order
    if request.method == "POST":
        if request.user.role == 'SENIOR_CLEANER' and order.senior_cleaner_id == request.user.id:
            task.status = 'IN_PROGRESS'
            task.save(update_fields=["status"])
            messages.info(request, f"Задача возвращена на доработку: {task.description}")
        else:
            messages.error(request, "Вы не можете вернуть эту задачу")
    return redirect("orders:order_detail", pk=order.pk)
