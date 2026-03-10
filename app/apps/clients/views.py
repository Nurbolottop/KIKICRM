from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from apps.clients import models as clients_models
from django.utils.timezone import now, timedelta
from apps.cms import models as cms_models
from apps.orders import models as orders_models
from django.db.models import Sum, Case, When, F, Value
from django.db.models.functions import Coalesce
from django.core.exceptions import ValidationError

# ✅ список всех клиентов
@login_required
def customer_list(request):
    settings = cms_models.Settings.objects.first()
    clients = clients_models.Client.objects.all().order_by("-updated_at")
    return render(request, "pages/system/others/customer/customer.html", locals())


# ✅ просмотр клиента
@login_required
def customer_view(request, pk):
    settings = cms_models.Settings.objects.first()
    client = get_object_or_404(clients_models.Client, pk=pk)
    # Calculate order statistics for this client
    orders_qs = orders_models.Order.objects.filter(client=client)
    # Total spent: prefer final_cost, fallback to estimated_cost
    total_agg = orders_qs.aggregate(
        total=Sum(
            Case(
                When(final_cost__isnull=False, then=F("final_cost")),
                default=F("estimated_cost"),
                output_field=orders_models.Order._meta.get_field("final_cost").__class__(),
            )
        )
    )
    client.orders_count = orders_qs.count()
    client.total_spent = total_agg.get("total") or 0
    client.first_order_date = orders_qs.order_by("date_time").values_list("date_time", flat=True).first()
    client.last_order_date = orders_qs.order_by("-date_time").values_list("date_time", flat=True).first()
    # Handle add note POST from the customer view page
    if request.method == "POST":
        note_text = (request.POST.get("note_text") or "").strip()
        if note_text:
            clients_models.ClientNote.objects.create(
                client=client,
                text=note_text,
                created_by=request.user,
            )
        return redirect("customer_view", pk=client.pk)
    return render(request, "pages/system/others/customer/customer-view.html", locals())


# ✅ добавление клиента
@login_required
def customer_add(request):
    settings = cms_models.Settings.objects.first()
    error_message = None
    if request.method == "POST":
        try:
            print(f"POST data: {request.POST}")
            print(f"FILES: {request.FILES}")
            
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
                birth_date=request.POST.get("birth_date") or None,
                gender=request.POST.get("gender") or None,
                category=request.POST.get("category") or "new",
                source=request.POST.get("source") or "other",
                photo=request.FILES.get("photo"),
                created_by=request.user,
                updated_by=request.user,
            )
            print(f"Client object created, saving...")
            client.save()
            print(f"Client saved successfully with ID: {client.pk}")
            
            # Create note if notes field is filled
            notes_text = (request.POST.get("notes") or "").strip()
            if notes_text:
                clients_models.ClientNote.objects.create(
                    client=client,
                    text=notes_text,
                    created_by=request.user,
                )
            
            if request.POST.get("add_another"):
                return redirect("customer_add")
            return redirect("customer")
        except ValidationError as e:
            print(f"ValidationError: {e}")
            if hasattr(e, 'message_dict'):
                error_message = "Ошибка валидации: " + ", ".join([msg for messages in e.message_dict.values() for msg in messages])
            else:
                error_message = f"Ошибка валидации: {str(e)}"
        except Exception as e:
            import traceback
            print(f"Exception: {e}")
            print(traceback.format_exc())
            error_message = f"Ошибка при сохранении: {str(e)}"
    return render(request, "pages/system/others/customer/customer-add.html", locals())


# ✅ редактирование клиента
@login_required
def customer_edit(request, pk):
    settings = cms_models.Settings.objects.first()
    client = get_object_or_404(clients_models.Client, pk=pk)
    notes = clients_models.ClientNote.objects.filter(client=client).order_by('-created_at')

    if request.method == "POST":
        client.first_name = request.POST.get("first_name")
        client.last_name = request.POST.get("last_name")
        client.middle_name = request.POST.get("middle_name")
        client.phone = request.POST.get("phone")
        client.email = request.POST.get("email")
        client.whatsapp = request.POST.get("whatsapp")
        client.address = request.POST.get("address")
        client.organization = request.POST.get("organization")
        client.birth_date = request.POST.get("birth_date") or None
        client.gender = request.POST.get("gender")
        client.category = request.POST.get("category")
        client.source = request.POST.get("source")
        if request.FILES.get("photo"):
            client.photo = request.FILES.get("photo")
        client.updated_by = request.user
        client.save()

        new_note_text = request.POST.get("new_note")
        if new_note_text:
            clients_models.ClientNote.objects.create(
                client=client,
                text=new_note_text,
                created_by=request.user
            )

        return redirect("customer_view", pk=client.pk)
    return render(request, "pages/system/others/customer/customer-edit.html", locals())


# ✅ клиенты, которых меняли за последние 7 дней
@login_required
def customer_delete(request, pk):
    """Удаление клиента"""
    client = get_object_or_404(clients_models.Client, pk=pk)
    if request.method == 'POST':
        client.delete()
        return redirect('customer')
    return redirect('customer_edit', pk=pk)


def recent_updates(request):
    settings = cms_models.Settings.objects.first()
    seven_days_ago = now() - timedelta(days=7)
    clients = clients_models.Client.objects.filter(updated_at__gte=seven_days_ago).select_related("updated_by")
    return render(request, "pages/system/others/customer/recent_updates.html", locals())
