from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views import View
from django.shortcuts import redirect
from django.db.models.deletion import ProtectedError
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from .models import Service, ServiceInventoryTemplate
from .forms import ServiceForm
from apps.inventory.models import InventoryItem


def sync_service_inventory_templates(service, request):
    item_ids = request.POST.getlist('inventory_item[]')
    quantities = request.POST.getlist('inventory_quantity[]')
    notes = request.POST.getlist('inventory_note[]')

    template_map = {}
    for index, raw_item_id in enumerate(item_ids):
        item_id = (raw_item_id or '').strip()
        if not item_id:
            continue

        quantity_raw = (quantities[index] if index < len(quantities) else '0').strip()
        note = (notes[index] if index < len(notes) else '').strip()
        try:
            quantity = float(quantity_raw or 0)
        except (TypeError, ValueError):
            quantity = 0

        if quantity <= 0:
            continue

        template_map[int(item_id)] = {
            'quantity': quantity,
            'note': note,
        }

    service.inventory_templates.exclude(inventory_item_id__in=list(template_map.keys())).delete()

    for inventory_item_id, payload in template_map.items():
        ServiceInventoryTemplate.objects.update_or_create(
            service=service,
            inventory_item_id=inventory_item_id,
            defaults={
                'quantity': payload['quantity'],
                'note': payload['note'],
            },
        )


class ServiceListView(LoginRequiredMixin, ListView):
    """Список услуг с пагинацией."""
    model = Service
    template_name = 'services/list.html'
    context_object_name = 'services'
    paginate_by = 20
    
    def get_queryset(self):
        return super().get_queryset().order_by('name')


class ServiceDetailView(LoginRequiredMixin, DetailView):
    """Детальная страница услуги."""
    model = Service
    template_name = 'services/detail.html'
    context_object_name = 'service'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['service'] = self.object
        context['inventory_templates'] = self.object.get_inventory_templates()
        return context


class ServiceAjaxUpdateView(LoginRequiredMixin, View):
    """AJAX обновление услуги."""
    def post(self, request, pk):
        try:
            service = Service.objects.filter(pk=pk).first()
            if not service:
                return JsonResponse({'ok': False, 'error': 'not_found'}, status=404)
            
            # Update fields
            service.service_type = request.POST.get('service_type', service.service_type)
            service.name = request.POST.get('name', service.name)
            service.description = request.POST.get('description', service.description)
            service.price = request.POST.get('price', service.price)
            service.room_count = request.POST.get('room_count', service.room_count)
            service.senior_cleaner_salary = request.POST.get('senior_cleaner_salary', service.senior_cleaner_salary)
            service.senior_cleaner_bonus = request.POST.get('senior_cleaner_bonus', service.senior_cleaner_bonus)
            service.senior_cleaner_count = request.POST.get('senior_cleaner_count', service.senior_cleaner_count)
            service.cleaner_count = request.POST.get('cleaner_count', service.cleaner_count)
            service.is_active = request.POST.get('is_active') == 'on'
            
            # Handle room-based checklist from JSON data
            checklist_data = request.POST.get('checklist_data')
            if checklist_data:
                try:
                    import json
                    rooms = json.loads(checklist_data)
                    # Filter empty rooms
                    service.checklist = [
                        room for room in rooms 
                        if room.get('name') or room.get('tasks')
                    ]
                except json.JSONDecodeError:
                    pass
            elif request.POST.getlist('checklist[]'):
                # Backward compatibility for flat checklist
                checklist = request.POST.getlist('checklist[]')
                service.checklist = [item for item in checklist if item.strip()]
            
            # Handle image
            if 'image' in request.FILES:
                service.image = request.FILES['image']
            
            service.save()
            
            sync_service_inventory_templates(service, request)
            
            return JsonResponse({
                'ok': True,
                'service': {
                    'id': service.id,
                    'service_type': service.service_type,
                    'name': service.name,
                    'description': service.description,
                    'price': str(service.price),
                    'room_count': service.room_count,
                    'senior_cleaner_salary': str(service.senior_cleaner_salary),
                    'senior_cleaner_bonus': str(service.senior_cleaner_bonus),
                    'senior_cleaner_count': service.senior_cleaner_count,
                    'cleaner_count': service.cleaner_count,
                    'is_active': service.is_active,
                    'checklist': service.checklist,
                    'image_url': service.image.url if service.image else None,
                }
            })
        except Exception as e:
            import traceback
            print(f"ServiceAjaxUpdateView error: {e}")
            print(traceback.format_exc())
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@method_decorator(require_POST, name='dispatch')
class ServiceChecklistTotalDeadlineView(LoginRequiredMixin, View):
    def post(self, request):
        checklist_data = request.POST.get('checklist_data') or ''
        if not checklist_data.strip():
            return JsonResponse({'ok': True, 'total_deadline_hours': 0})

        try:
            import json

            rooms = json.loads(checklist_data)
            total = 0.0
            if isinstance(rooms, list):
                for room in rooms:
                    if not isinstance(room, dict):
                        continue
                    value = room.get('deadline_hours')
                    if value in (None, ''):
                        continue
                    try:
                        total += float(value)
                    except (TypeError, ValueError):
                        continue
            return JsonResponse({'ok': True, 'total_deadline_hours': total})
        except Exception:
            return JsonResponse({'ok': False, 'error': 'invalid_payload'}, status=400)


class ServiceCreateView(LoginRequiredMixin, CreateView):
    """Создание новой услуги."""
    model = Service
    form_class = ServiceForm
    template_name = 'services/form.html'
    success_url = reverse_lazy('services_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Новая услуга'
        context['button_text'] = 'Создать'
        context['inventory_items'] = InventoryItem.objects.filter(is_active=True).select_related('category').order_by(
            'item_type', 'category__name', 'name'
        )
        context['inventory_templates'] = []
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Сохраняем чеклист из JSON данных
        checklist_data = self.request.POST.get('checklist_data')
        if checklist_data:
            try:
                import json
                rooms = json.loads(checklist_data)
                # Фильтруем пустые комнаты
                self.object.checklist = [
                    room for room in rooms 
                    if room.get('name') or room.get('tasks')
                ]
                self.object.save()
            except json.JSONDecodeError:
                pass

        sync_service_inventory_templates(self.object, self.request)

        try:
            from apps.notifications.services.telegram_service import TelegramService

            user = self.request.user
            user_display = (
                (getattr(user, 'full_name', '') or '').strip()
                or getattr(user, 'username', '')
                or getattr(user, 'phone', '')
                or str(user)
            )
            text = (
                f"🆕 <b>Новая услуга добавлена</b>\n\n"
                f"Название: <b>{self.object.name}</b>\n"
                f"Цена: {self.object.price}\n"
                f"Пользователь: {user_display}"
            )
            TelegramService().send_status_change_message(text)
        except Exception:
            pass
        return response


class ServiceUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование услуги."""
    model = Service
    form_class = ServiceForm
    template_name = 'services/form.html'

    def get_success_url(self):
        return reverse_lazy('service_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Редактирование услуги'
        context['button_text'] = 'Сохранить'
        context['service'] = self.object
        context['inventory_items'] = InventoryItem.objects.filter(is_active=True).select_related('category').order_by(
            'item_type', 'category__name', 'name'
        )
        context['inventory_templates'] = self.object.get_inventory_templates()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        # Сохраняем чеклист из JSON данных
        checklist_data = self.request.POST.get('checklist_data')
        if checklist_data:
            try:
                import json
                rooms = json.loads(checklist_data)
                # Фильтруем пустые комнаты
                self.object.checklist = [
                    room for room in rooms
                    if room.get('name') or room.get('tasks')
                ]
                self.object.save()
            except json.JSONDecodeError:
                pass
        sync_service_inventory_templates(self.object, self.request)
        return response


class ServiceDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление услуги."""
    model = Service
    template_name = 'services/delete.html'
    success_url = reverse_lazy('services_list')
    context_object_name = 'service'

    def post(self, request, *args, **kwargs):
        from django.contrib import messages

        self.object = self.get_object()
        try:
            self.object.delete()
            messages.success(request, f'Услуга "{self.object.name}" успешно удалена.')
        except ProtectedError:
            messages.error(request, f'Нельзя удалить услугу "{self.object.name}", так как она используется в заказах.')
        return redirect(self.get_success_url())
