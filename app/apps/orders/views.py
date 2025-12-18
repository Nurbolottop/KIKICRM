from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.http import JsonResponse
from apps.orders import models as orders_models
from apps.clients import models as clients_models
from apps.cms import models as cms_models


@login_required
def order_list(request):
    settings = cms_models.Settings.objects.first()
    orders = orders_models.Order.objects.all()
    
    
    # Фильтрация по поисковому запросу
    search_query = request.GET.get('q', '')
    if search_query:
        orders = orders.filter(
            models.Q(code__icontains=search_query) |
            models.Q(client__first_name__icontains=search_query) |
            models.Q(client__last_name__icontains=search_query) |
            models.Q(client__phone__icontains=search_query) |
            models.Q(address__icontains=search_query)
        )
    
    # Фильтрация по статусу оператора
    status_operator = request.GET.get('status_operator', '')
    if status_operator:
        orders = orders.filter(status_operator=status_operator)
    
    # Фильтрация по статусу менеджера
    status_manager = request.GET.get('status_manager', '')
    if status_manager:
        orders = orders.filter(status_manager=status_manager)
    
    # Фильтрация по приоритету
    priority = request.GET.get('priority', '')
    if priority:
        orders = orders.filter(priority=priority)
    
    # Фильтрация по типу помещения
    property_type = request.GET.get('property_type', '')
    if property_type:
        orders = orders.filter(property_type=property_type)
    
    # Фильтрация по услуге
    service = request.GET.get('service', '')
    if service:
        orders = orders.filter(service_id=service)
    
    # Фильтрация по дате
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        orders = orders.filter(date_time__gte=date_from)
    if date_to:
        orders = orders.filter(date_time__lte=date_to)
    
    # Получаем данные для фильтров
    services = cms_models.Services.objects.all()
    
    return render(request, "pages/system/others/orders/order.html", locals())


@login_required
def order_detail(request, pk):
    settings = cms_models.Settings.objects.first()
    order = get_object_or_404(orders_models.Order, pk=pk)
    # Список описаний шаблонов задач услуги для подсветки доп. задач
    template_descriptions = []
    if order.service and hasattr(order.service, 'task_templates'):
        template_descriptions = list(order.service.task_templates.values_list('description', flat=True))
    context = {
        'settings': settings,
        'order': order,
        'template_descriptions': template_descriptions,
    }
    return render(request, "pages/system/others/orders/order-view.html", context)


@login_required
def order_create(request):
    settings = cms_models.Settings.objects.first()
    if request.method == "POST":
        client_id = request.POST.get("client")
        client = get_object_or_404(clients_models.Client, pk=client_id)

        # Accept both new and legacy field names from the form
        service_id = request.POST.get("service") or request.POST.get("service_type")

        order = orders_models.Order.objects.create(
            client=client,
            category=request.POST.get("category"),
            service_id=service_id,
            address=request.POST.get("address"),
            property_type=request.POST.get("property_type") or None,
            date_time=request.POST.get("date_time"),
            estimated_cost=request.POST.get("estimated_cost") or None,
            estimated_area=request.POST.get("estimated_area") or None,
            notes=request.POST.get("notes"),
            channel=request.POST.get("channel"),
            source=request.POST.get("source"),
            priority=request.POST.get("priority"),
            operator=request.user,
        )

        # Если статус выбран на форме — сохранить его, иначе оставить значение по умолчанию модели
        form_status = request.POST.get("status_operator")
        if form_status:
            order.status_operator = form_status
            order.save(update_fields=["status_operator"])

        # Автодобавление задач из шаблонов услуги сразу при создании
        if order.service and hasattr(order.service, 'task_templates'):
            existing_desc = set()
            for t in order.tasks.all():
                existing_desc.add(t.description)
            for template in order.service.task_templates.all():
                if template.description not in existing_desc:
                    orders_models.Task.objects.create(
                        order=order,
                        description=template.description,
                        status='IN_PROGRESS'
                    )
        messages.success(request, f"Заказ {order.code} успешно создан")
        return redirect("customer_view", pk=order.client.pk)

    clients = clients_models.Client.objects.all()
    services = cms_models.Services.objects.all()
    return render(request, "pages/system/others/orders/order-new.html", locals())


@login_required
def order_update(request, pk):
    """Редактирование заказа менеджером"""
    
    settings = cms_models.Settings.objects.first()
    order = get_object_or_404(orders_models.Order, pk=pk)
    
    # Списки клинеров удалены

    if request.method == "POST":
        action = request.POST.get("action")
        
        # Быстрые действия со статусом (из панели менеджера)
        if action in ["quick_status", "quick_complete"]:
            status = request.POST.get("status_manager")
            if status:
                order.status_manager = status
                order.save(update_fields=["status_manager"])
                messages.success(request, f"Статус заказа {order.code} изменён на {order.get_status_manager_display()}")
            return redirect("orders:order_detail", pk=order.pk)
        
        # Полное редактирование заказа
        # Обновляем финансовые данные
        order.final_cost = request.POST.get("final_cost") or order.final_cost
        order.final_area = request.POST.get("final_area") or order.final_area
        order.manager_comment = request.POST.get("manager_comment") or order.manager_comment
        order.status_manager = request.POST.get("status_manager") or order.status_manager
        order.deadline = request.POST.get("deadline") or order.deadline
        
        order.save()
        
        
        messages.success(request, f"Заказ {order.code} обновлён")
        return redirect("orders:order_detail", pk=order.pk)

    # Список описаний шаблонов задач услуги для подсветки доп. задач
    template_descriptions = []
    if order.service and hasattr(order.service, 'task_templates'):
        template_descriptions = list(order.service.task_templates.values_list('description', flat=True))

    context = {
        'settings': settings,
        'order': order,
        'template_descriptions': template_descriptions,
    }
    return render(request, "pages/system/others/orders/edit/order-manager-edit.html", context)


@login_required
def order_operator_update(request, pk):
    """Редактирование заказа оператором"""
    settings = cms_models.Settings.objects.first()
    order = get_object_or_404(orders_models.Order, pk=pk)
    
    if request.method == "POST":
        # Поля, которые может редактировать оператор
        order.category = request.POST.get("category", order.category)
        
        service_id = request.POST.get("service")
        service_changed = False
        if service_id and str(order.service_id) != str(service_id):
            order.service_id = service_id                     
            service_changed = True
            
        order.address = request.POST.get("address", order.address)
        order.property_type = request.POST.get("property_type") or None
        order.date_time = request.POST.get("date_time", order.date_time)
        order.estimated_cost = request.POST.get("estimated_cost") or order.estimated_cost
        order.estimated_area = request.POST.get("estimated_area") or order.estimated_area
        order.notes = request.POST.get("notes", order.notes)
        order.channel = request.POST.get("channel", order.channel)
        order.source = request.POST.get("source", order.source)
        order.priority = request.POST.get("priority", order.priority)
        order.status_operator = request.POST.get("status_operator", order.status_operator)
        
        order.save()
        
        messages.success(request, f"Заказ {order.code} успешно обновлён")
        return redirect("orders:order_detail", pk=order.pk)
    
    clients = clients_models.Client.objects.all()
    services = cms_models.Services.objects.all()
    return render(request, "pages/system/others/orders/edit/order-operator-edit.html", locals())


@login_required
def order_send_to_manager(request, pk):
    """Передача заказа менеджеру (автоматически меняет статус на ACCEPTED)"""
    order = get_object_or_404(orders_models.Order, pk=pk)
    
    # Меняем статус оператора на "Принято"
    order.status_operator = orders_models.Order.OperatorStatus.ACCEPTED
    # Устанавливаем статус менеджера на "Назначен"
    order.status_manager = orders_models.Order.ManagerStatus.ASSIGNED
    order.save()
    
    # Автоматически создаем задачи из шаблонов для выбранной услуги (без дублей)
    if order.service and hasattr(order.service, 'task_templates'):
        task_templates = order.service.task_templates.all()
        existing_desc = set(order.tasks.values_list('description', flat=True))
        added = 0
        for template in task_templates:
            if template.description not in existing_desc:
                orders_models.Task.objects.create(
                    order=order,
                    description=template.description,
                    status='IN_PROGRESS'
                )
                added += 1
        if added:
            messages.info(request, f"Автоматически добавлено {added} задач(и) из шаблона")
    
    messages.success(request, f"Заказ {order.code} успешно передан менеджеру")
    return redirect("orders:order_detail", pk=order.pk)


@login_required
def task_create(request, order_id):
    settings = cms_models.Settings.objects.first()
    order = get_object_or_404(orders_models.Order, pk=order_id)

    if request.method == "POST":
        orders_models.Task.objects.create(
            order=order,
            description=request.POST.get("description"),
        )
        messages.success(request, "Задача добавлена")
        return redirect("orders:order_manager_update", pk=order.pk)

    return render(request, "pages/system/others/orders/task-form.html", locals())


@login_required
def task_update(request, pk):
    settings = cms_models.Settings.objects.first()
    task = get_object_or_404(orders_models.Task, pk=pk)

    if request.method == "POST":
        task.description = request.POST.get("description", task.description)
        task.status = request.POST.get("status", task.status)
        
        cleaner_id = request.POST.get("cleaner")
        if cleaner_id:
            task.cleaner_id = cleaner_id
        else:
            task.cleaner = None
            
        if "photo_before" in request.FILES:
            task.photo_before = request.FILES["photo_before"]
        if "photo_after" in request.FILES:
            task.photo_after = request.FILES["photo_after"]
        task.comment = request.POST.get("comment", task.comment)
        task.save()

        messages.success(request, "Задача обновлена")
        return redirect("orders:order_manager_update", pk=task.order.pk)

    return render(request, "pages/system/others/orders/task-form.html", locals())


@login_required
def task_delete(request, pk):
    """Удаление задачи"""
    task = get_object_or_404(orders_models.Task, pk=pk)
    order_id = task.order.pk
    
    if request.method == "POST":
        task.delete()
        messages.success(request, "Задача удалена")
    
    return redirect("orders:order_manager_update", pk=order_id)


@login_required
def order_revert_to_work(request, pk):
    """Вернуть заказ с проверки обратно в работу. Доступно для MANAGER, FOUNDER."""
    from django.utils import timezone  # noqa: F401 (может пригодиться в будущем)

    order = get_object_or_404(orders_models.Order, pk=pk)

    if request.user.role not in ['MANAGER', 'FOUNDER']:
        messages.error(request, "У вас нет прав для этого действия")
        return redirect("orders:order_detail", pk=pk)
    if request.method == "POST":
        if order.status_manager == 'PENDING_REVIEW':
            order.status_manager = 'IN_PROGRESS'
            order.work_finished_at = None
            order.save()
            messages.success(request, f"Заказ {order.code} возвращён в работу")
        else:
            messages.info(request, "Заказ не находится на проверке")
        return redirect("orders:order_detail", pk=pk)
    
    return redirect("orders:order_detail", pk=pk)
@login_required
def order_calendar_events(request):
    status = request.GET.get("status", "all").lower()

    qs = orders_models.Order.objects.select_related("client", "service")

    if status == "completed":
        qs = qs.filter(status_manager=orders_models.Order.ManagerStatus.COMPLETED)
    elif status == "declined":
        qs = qs.filter(
            models.Q(status_manager=orders_models.Order.ManagerStatus.DECLINED)
            | models.Q(status_operator=orders_models.Order.OperatorStatus.DECLINED)
        )
    elif status == "active":
        qs = qs.filter(
            models.Q(status_manager__in=[
                orders_models.Order.ManagerStatus.ASSIGNED,
                orders_models.Order.ManagerStatus.IN_PROGRESS,
                orders_models.Order.ManagerStatus.PENDING_REVIEW,
            ])
            | models.Q(status_manager__isnull=True)
        ).exclude(
            models.Q(status_manager=orders_models.Order.ManagerStatus.COMPLETED)
            | models.Q(status_manager=orders_models.Order.ManagerStatus.DECLINED)
            | models.Q(status_operator=orders_models.Order.OperatorStatus.DECLINED)
        )

    events = []
    for order in qs:
        if order.status_manager == orders_models.Order.ManagerStatus.COMPLETED:
            category = "completed"
        elif (
            order.status_manager == orders_models.Order.ManagerStatus.DECLINED
            or order.status_operator == orders_models.Order.OperatorStatus.DECLINED
        ):
            category = "declined"
        else:
            category = "active"

        title_parts = [order.code]
        if order.client:
            title_parts.append(str(order.client))
        if order.service:
            title_parts.append(order.service.title)

        events.append(
            {
                "id": order.id,
                "title": " | ".join(title_parts),
                "start": order.date_time.isoformat() if order.date_time else None,
                "end": order.deadline.isoformat() if order.deadline else None,
                "extendedProps": {
                    "code": order.code,
                    "status_manager": order.status_manager,
                    "status_operator": order.status_operator,
                    "category": category,
                    "address": order.address,
                },
            }
        )

    return JsonResponse(events, safe=False)


@login_required
def order_calendar_page(request):
    settings = cms_models.Settings.objects.first()
    return render(request, "pages/system/others/orders/order_calendar.html", {"settings": settings})

@login_required
def order_finish_work(request, pk):
    """Менеджер/Основатель завершает работу и отправляет заказ на проверку"""
    from django.utils import timezone

    order = get_object_or_404(orders_models.Order, pk=pk)

    # Только менеджер или основатель
    if request.user.role not in ['MANAGER', 'FOUNDER']:
        messages.error(request, "У вас нет прав для этого действия")
        return redirect("orders:order_detail", pk=pk)

    if request.method == "POST":
        order.work_finished_at = timezone.now()
        order.status_manager = orders_models.Order.ManagerStatus.PENDING_REVIEW
        order.save()
        messages.success(request, f"Работа по заказу {order.code} завершена и отправлена на проверку")
        return redirect("orders:order_detail", pk=pk)

    return redirect("orders:order_detail", pk=pk)

@login_required
def order_quality_check(request, pk):
    """Проверка качества менеджером"""
    from django.utils import timezone
    
    order = get_object_or_404(orders_models.Order, pk=pk)
    
    # Только менеджер или основатель
    if request.user.role not in ['MANAGER', 'FOUNDER']:
        messages.error(request, "Только менеджер может проверять качество")
        return redirect("orders:order_detail", pk=pk)
    
    if request.method == "POST":
        # Получаем данные из формы
        quality_rating = request.POST.get("quality_rating")
        quality_comment = request.POST.get("quality_comment")
        decision = request.POST.get("decision")  # COMPLETED или IN_PROGRESS
        
        # Сохраняем оценку
        order.quality_rating = quality_rating
        order.quality_comment = quality_comment
        order.reviewed_at = timezone.now()
        order.reviewed_by = request.user
        order.status_manager = decision
        order.save()
        
        if decision == 'COMPLETED':
            messages.success(request, f"Заказ {order.code} принят и завершён. Оценка: {quality_rating}/5")
        else:
            messages.warning(request, f"Заказ {order.code} отправлен на переделку")
        
        return redirect("orders:order_detail", pk=pk)
    
    return redirect("orders:order_detail", pk=pk)
