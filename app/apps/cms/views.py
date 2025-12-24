from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from apps.cms import models as cms_models
from apps.contacts import models as contacts_models
from apps.contacts import views as contacts_views
from apps.cms.forms import ServiceForm, ServiceTaskTemplateForm
from apps.users.models import User


@login_required
def index(request):
    settings = cms_models.Settings.objects.first()
    return render(request, 'pages/system/others/index.html', locals())


def _require_services_access(request):
    if request.user.role not in [User.Role.FOUNDER, User.Role.MANAGER, User.Role.OPERATOR]:
        messages.error(request, "У вас нет доступа")
        return False
    return True


@login_required
def services_list(request):
    settings = cms_models.Settings.objects.first()
    if not _require_services_access(request):
        return redirect("index")
    services = cms_models.Services.objects.all().order_by('order', 'title')
    return render(request, "pages/system/others/services/services_list.html", locals())


@login_required
def service_add(request):
    settings = cms_models.Settings.objects.first()
    if not _require_services_access(request):
        return redirect("index")

    if request.method == "POST":
        form = ServiceForm(request.POST, request.FILES)
        if form.is_valid():
            service = form.save(commit=False)
            if getattr(service, "order", None) in (None, ""):
                max_order = cms_models.Services.objects.aggregate(models.Max("order")).get("order__max") or 0
                service.order = max_order + 1
            service.save()
            messages.success(request, "Услуга добавлена")
            return redirect("services_list")
    else:
        form = ServiceForm()

    return render(request, "pages/system/others/services/service_add.html", locals())


@login_required
def service_view(request, pk):
    settings = cms_models.Settings.objects.first()
    if not _require_services_access(request):
        return redirect("index")

    service = get_object_or_404(cms_models.Services, pk=pk)
    task_templates = service.task_templates.all().order_by("order", "id")
    task_form = ServiceTaskTemplateForm()
    return render(request, "pages/system/others/services/service_view.html", locals())


@login_required
def service_task_add(request, pk):
    settings = cms_models.Settings.objects.first()
    if not _require_services_access(request):
        return redirect("index")

    service = get_object_or_404(cms_models.Services, pk=pk)
    if request.method != "POST":
        return redirect("service_view", pk=service.pk)

    form = ServiceTaskTemplateForm(request.POST)
    if form.is_valid():
        template = form.save(commit=False)
        template.service = service
        max_order = service.task_templates.aggregate(models.Max("order")).get("order__max") or 0
        template.order = max_order + 1
        template.save()
        messages.success(request, "Задача добавлена")
    else:
        messages.error(request, "Не удалось добавить задачу")

    return redirect("service_view", pk=service.pk)


@login_required
def service_task_edit(request, pk, task_id):
    settings = cms_models.Settings.objects.first()
    if not _require_services_access(request):
        return redirect("index")

    service = get_object_or_404(cms_models.Services, pk=pk)
    template = get_object_or_404(cms_models.ServiceTaskTemplate, pk=task_id, service=service)
    if request.method != "POST":
        return redirect("service_view", pk=service.pk)

    form = ServiceTaskTemplateForm(request.POST, instance=template)
    if form.is_valid():
        form.save()
        messages.success(request, "Задача обновлена")
    else:
        messages.error(request, "Не удалось обновить задачу")

    return redirect("service_view", pk=service.pk)


@login_required
def service_task_delete(request, pk, task_id):
    settings = cms_models.Settings.objects.first()
    if not _require_services_access(request):
        return redirect("index")

    service = get_object_or_404(cms_models.Services, pk=pk)
    template = get_object_or_404(cms_models.ServiceTaskTemplate, pk=task_id, service=service)
    if request.method == "POST":
        template.delete()
        messages.success(request, "Задача удалена")
    return redirect("service_view", pk=service.pk)


@login_required
def service_edit(request, pk):
    settings = cms_models.Settings.objects.first()
    if not _require_services_access(request):
        return redirect("index")

    service = get_object_or_404(cms_models.Services, pk=pk)
    if request.method == "POST":
        form = ServiceForm(request.POST, request.FILES, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, "Услуга обновлена")
            return redirect("services_list")
    else:
        form = ServiceForm(instance=service)

    return render(request, "pages/system/others/services/service_edit.html", locals())


@login_required
def service_delete(request, pk):
    settings = cms_models.Settings.objects.first()
    if not _require_services_access(request):
        return redirect("index")

    service = get_object_or_404(cms_models.Services, pk=pk)
    if request.method != "POST":
        return redirect("services_list")

    service.delete()
    messages.success(request, "Услуга удалена")
    return redirect("services_list")
