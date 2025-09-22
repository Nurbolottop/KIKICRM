from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from apps.clients import models as clients_models
from django.utils.timezone import now, timedelta
from apps.cms import models as cms_models

# ✅ список всех клиентов
@login_required
def customer_list(request):
    settings = cms_models.Settings.objects.first()
    clients = clients_models.Client.objects.all().order_by("-updated_at")
    return render(request, "pages/manager/others/customer/customer.html", locals())


# ✅ просмотр клиента
@login_required
def customer_view(request, pk):
    settings = cms_models.Settings.objects.first()
    client = get_object_or_404(clients_models.Client, pk=pk)
    return render(request, "pages/manager/others/customer/customer-view.html", locals())


# ✅ добавление клиента
@login_required
def customer_add(request):
    settings = cms_models.Settings.objects.first()
    if request.method == "POST":
        client = clients_models.Client(
            first_name=request.POST.get("first_name"),
            last_name=request.POST.get("last_name"),
            middle_name=request.POST.get("middle_name"),
            phone=request.POST.get("phone"),
            email=request.POST.get("email"),
            whatsapp=request.POST.get("whatsapp"),
            telegram_id=request.POST.get("telegram_id"),
            address=request.POST.get("address"),
            organization=request.POST.get("organization"),
            age=request.POST.get("age") or None,
            gender=request.POST.get("gender"),
            category=request.POST.get("category"),
            source=request.POST.get("source"),
            photo=request.FILES.get("photo"),
            created_by=request.user,
            updated_by=request.user,
        )
        client.save()
        return redirect("customer")
    return render(request, "pages/manager/others/customer/customer-add.html", locals())


# ✅ редактирование клиента
@login_required
def customer_edit(request, pk):
    settings = cms_models.Settings.objects.first()
    client = get_object_or_404(clients_models.Client, pk=pk)
    if request.method == "POST":
        client.first_name = request.POST.get("first_name")
        client.last_name = request.POST.get("last_name")
        client.middle_name = request.POST.get("middle_name")
        client.phone = request.POST.get("phone")
        client.email = request.POST.get("email")
        client.whatsapp = request.POST.get("whatsapp")
        client.telegram_id = request.POST.get("telegram_id")
        client.address = request.POST.get("address")
        client.organization = request.POST.get("organization")
        client.age = request.POST.get("age") or None
        client.gender = request.POST.get("gender")
        client.category = request.POST.get("category")
        client.source = request.POST.get("source")
        if request.FILES.get("photo"):
            client.photo = request.FILES.get("photo")
        client.updated_by = request.user
        client.save()
        return redirect("customer_view", pk=client.pk)
    return render(request, "pages/manager/others/customer/customer-edit.html", locals())


# ✅ клиенты, которых меняли за последние 7 дней
@login_required
def customer_delete(request, pk):
    """Удаление клиента"""
    client = get_object_or_404(clients_models.Client, pk=pk)
    if request.method == 'POST':
        client.delete()
        return redirect('customer')
    return redirect('customer_edit', pk=pk)


@login_required
def recent_updates(request):
    settings = cms_models.Settings.objects.first()
    seven_days_ago = now() - timedelta(days=7)
    clients = clients_models.Client.objects.filter(updated_at__gte=seven_days_ago).select_related("updated_by")
    return render(request, "pages/manager/others/customer/recent_updates.html", locals())
