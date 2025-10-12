from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
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
    return render(request, "pages/system/others/orders/order-view.html", locals())


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

        messages.success(request, f"Заказ {order.code} успешно создан")
        return redirect("customer_view", pk=order.client.pk)

    clients = clients_models.Client.objects.all()
    services = cms_models.Services.objects.all()
    return render(request, "pages/system/others/orders/order-new.html", locals())


@login_required
def order_update(request, pk):
    settings = cms_models.Settings.objects.first()
    order = get_object_or_404(orders_models.Order, pk=pk)

    if request.method == "POST":
        order.final_cost = request.POST.get("final_cost") or order.final_cost
        order.final_area = request.POST.get("final_area") or order.final_area
        order.manager_comment = request.POST.get("manager_comment") or order.manager_comment
        order.status_manager = request.POST.get("status_manager") or order.status_manager
        order.deadline = request.POST.get("deadline") or order.deadline
        order.save()

        messages.success(request, f"Заказ {order.code} обновлён")
        return redirect("orders:order_detail", pk=order.pk)

    return render(request, "pages/system/others/orders/order-edit.html", locals())


@login_required
def order_operator_update(request, pk):
    """Редактирование заказа оператором"""
    settings = cms_models.Settings.objects.first()
    order = get_object_or_404(orders_models.Order, pk=pk)
    
    if request.method == "POST":
        # Поля, которые может редактировать оператор
        order.category = request.POST.get("category", order.category)
        
        service_id = request.POST.get("service")
        if service_id:
            order.service_id = service_id
            
        order.address = request.POST.get("address", order.address)
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
    
    messages.success(request, f"Заказ {order.code} успешно передан менеджеру")
    return redirect("orders:order_detail", pk=order.pk)


@login_required
def task_create(request, order_id):
    settings = cms_models.Settings.objects.first()
    order = get_object_or_404(orders_models.Order, pk=order_id)

    if request.method == "POST":
        orders_models.Task.objects.create(
            order=order,
            cleaner_id=request.POST.get("cleaner"),
            description=request.POST.get("description"),
        )
        messages.success(request, "Задача добавлена")
        return redirect("orders:order_detail", pk=order.pk)

    return render(request, "pages/system/others/orders/task-form.html", locals())


@login_required
def task_update(request, pk):
    settings = cms_models.Settings.objects.first()
    task = get_object_or_404(orders_models.Task, pk=pk)

    if request.method == "POST":
        task.status = request.POST.get("status", task.status)
        if "photo_before" in request.FILES:
            task.photo_before = request.FILES["photo_before"]
        if "photo_after" in request.FILES:
            task.photo_after = request.FILES["photo_after"]
        task.comment = request.POST.get("comment", task.comment)
        task.save()

        messages.success(request, "Задача обновлена")
        return redirect("orders:order_detail", pk=task.order.pk)

    return render(request, "pages/system/others/orders/task-update.html", locals())
