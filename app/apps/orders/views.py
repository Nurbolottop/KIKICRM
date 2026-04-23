from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
import logging
from decimal import Decimal, InvalidOperation

from apps.common.permissions import (
    can_view_orders, can_create_orders, can_edit_orders, can_delete_orders,
    can_assign_cleaners, PermissionRequiredMixin
)
from .models import Order, OrderEmployee, OrderInventoryUsage, OrderPhoto, RefuseSettings, OrderStatus, OrderExtraService
from .forms import OrderForm
from apps.orders.services.order_status_service import OrderStatusChecker, OrderStatusService
from apps.notifications.services.notification_service import NotificationService
from apps.inventory.models import InventoryItem, InventoryTransaction, TransactionType
from apps.services.models import ServiceInventoryTemplate, ExtraService


logger = logging.getLogger(__name__)


def _build_order_copy_text(order):
    russian_months = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }

    client = order.client
    client_name = client.get_full_name() if client else '—'
    client_phone = client.phone if client and client.phone else '—'
    client_address = order.address or (client.address if client and client.address else '—')

    scheduled_date = '—'
    if order.scheduled_date:
        month_name = russian_months.get(order.scheduled_date.month, '')
        scheduled_date = f"{order.scheduled_date.day} {month_name}".strip()
    scheduled_time = order.scheduled_time.strftime('%H:%M') if order.scheduled_time else '—'

    rooms_count = order.rooms_count if order.rooms_count is not None else '—'
    area = f"{order.area:.2f}" if order.area is not None else '—'
    bathrooms = order.bathrooms_count if order.bathrooms_count is not None else '—'
    windows = order.windows_count if order.windows_count is not None else '—'

    service_name = order.service.name if order.service else '—'
    # Доп. услуги: сначала из OrderExtraService, если нет — из work_scope (текст)
    order_extra_svcs = order.order_extra_services.select_related('extra_service').all()
    if order_extra_svcs.exists():
        extra_services_lines = [
            f"- {oes.extra_service.name} x{oes.quantity} = {oes.total_price:.0f} сом"
            for oes in order_extra_svcs
        ]
        extra_services = '\n'.join(extra_services_lines)
    elif order.work_scope:
        extra_services = order.work_scope
    else:
        extra_services = 'Нет'
    special_notes = order.comment if order.comment else '—'

    payment_method = getattr(order, 'payment_method', None) or 'наличка'
    prepayment_text = f"• Задаток: {order.prepayment_amount:.2f} сом\n" if order.prepayment_amount else ''

    if order.preliminary_price and order.preliminary_price > 0:
        total_text = f"{order.preliminary_price:.2f} сом (предварительно)"
    elif order.price and order.price > 0:
        total_text = f"{order.price:.2f} сом"
    else:
        total_text = 'Сумму посчитать на месте'

    order_code = order.order_code or f"#{order.id}"
    return (
        f"🆕 Заказ {order_code}\n\n"
        f"Клиент:\n"
        f"• ФИО: {client_name}\n"
        f"• Телефон: {client_phone}\n"
        f"• Адрес: {client_address}\n\n"
        f"Детали уборки:\n"
        f"• Дата и время: {scheduled_date}, {scheduled_time}\n"
        f"• Вид помещения: {order.get_property_type_display()}\n"
        f"• Комнаты: {rooms_count}\n"
        f"• Площадь: {area} м²\n"
        f"• Санузлы: {bathrooms}\n"
        f"• Окна: {windows}\n"
        f"• После ремонта: {'Да' if order.after_renovation else 'Нет'}\n\n"
        f"Услуги:\n"
        f"• Основная: {service_name}\n"
        f"• Доп.услуги: {extra_services}\n"
        f"• Особые пожелания: {special_notes}\n\n"
        f"Оплата:\n"
        f"• Способ: {payment_method}\n"
        f"{prepayment_text}\n"
        f"💰 Итоговая сумма: {total_text}\n\n"
        f"⚠️ Примечание:\n"
        f"1. Клиент должен проверить работу сразу после уборки. Жалобы после ухода клинеров не принимаются.\n\n"
        f"2. В доме, в квартире и в объекте должна быть вода, в каждой комнате должен быть свет.\n\n"
        f"3. Оплату строго давать менеджеру если наличка, если перевод на номер мбанк +996 221 241 172 Кишимжан К и чек оператору."
    )


def _parse_decimal(value, default='0'):
    try:
        if value in (None, ''):
            return Decimal(default)
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def build_inventory_usage_initial(order):
    existing = list(
        order.inventory_usages.select_related('inventory_item', 'inventory_item__category').order_by(
            'inventory_item__item_type', 'inventory_item__category__name', 'inventory_item__name'
        )
    )
    if existing:
        return existing, False

    if not order.service_id:
        return [], False

    templates = list(
        ServiceInventoryTemplate.objects.filter(service=order.service).select_related(
            'inventory_item', 'inventory_item__category'
        ).order_by('inventory_item__item_type', 'inventory_item__category__name', 'inventory_item__name')
    )
    return templates, True


def sync_order_inventory_usage(order, request):
    item_ids = request.POST.getlist('usage_inventory_item[]')
    quantities = request.POST.getlist('usage_quantity[]')
    notes = request.POST.getlist('usage_note[]')

    parsed_rows = []
    for index, raw_item_id in enumerate(item_ids):
        item_id = (raw_item_id or '').strip()
        if not item_id:
            continue

        quantity = _parse_decimal(quantities[index] if index < len(quantities) else '0')
        note = (notes[index] if index < len(notes) else '').strip()
        if quantity <= 0:
            continue
        parsed_rows.append((int(item_id), quantity, note))

    item_map = {item.id: item for item in InventoryItem.objects.filter(id__in=[row[0] for row in parsed_rows])}
    existing_usages = {usage.inventory_item_id: usage for usage in order.inventory_usages.select_related('inventory_item')}
    touched_ids = []

    for item_id, quantity, note in parsed_rows:
        item = item_map.get(item_id)
        if not item:
            continue
        usage = existing_usages.get(item_id)
        previous_quantity = usage.quantity if usage else Decimal('0')
        delta = quantity - previous_quantity

        if usage:
            usage.quantity = quantity
            usage.note = note
            usage.save(update_fields=['quantity', 'note', 'updated_at'])
        else:
            usage = OrderInventoryUsage.objects.create(
                order=order,
                inventory_item=item,
                quantity=quantity,
                note=note,
            )

        touched_ids.append(usage.id)
        if delta != 0:
            transaction_type = TransactionType.OUT if delta > 0 else TransactionType.IN
            InventoryTransaction.objects.create(
                item=item,
                transaction_type=transaction_type,
                quantity=abs(delta),
                order=order,
                usage=usage,
                comment=f'Синхронизация использования инвентаря по заказу {order.order_code}',
            )

    for usage in order.inventory_usages.exclude(id__in=touched_ids):
        if usage.quantity > 0:
            InventoryTransaction.objects.create(
                item=usage.inventory_item,
                transaction_type=TransactionType.IN,
                quantity=usage.quantity,
                order=order,
                usage=usage,
                comment=f'Возврат инвентаря после удаления строки использования по заказу {order.order_code}',
            )
        usage.delete()


def sync_order_extra_services(order, request):
    """Синхронизирует доп. услуги заказа на основе POST-данных."""
    service_ids = request.POST.getlist('extra_service_id[]')
    quantities = request.POST.getlist('extra_service_qty[]')
    notes = request.POST.getlist('extra_service_note[]')

    parsed = []
    for idx, raw_id in enumerate(service_ids):
        sid = (raw_id or '').strip()
        if not sid:
            continue
        try:
            qty = max(1, int(quantities[idx]) if idx < len(quantities) else 1)
        except (ValueError, TypeError):
            qty = 1
        note = (notes[idx] if idx < len(notes) else '').strip()
        parsed.append((int(sid), qty, note))

    kept_ids = []
    svc_map = {s.id: s for s in ExtraService.objects.filter(id__in=[r[0] for r in parsed])}

    for svc_id, qty, note in parsed:
        svc = svc_map.get(svc_id)
        if not svc:
            continue
        obj, created = OrderExtraService.objects.update_or_create(
            order=order,
            extra_service=svc,
            defaults={
                'quantity': qty,
                'price_at_order': svc.price,
                'note': note,
            }
        )
        kept_ids.append(obj.id)

    # Удаляем те доп. услуги, которых нет в новом списке
    order.order_extra_services.exclude(id__in=kept_ids).delete()


class OrderListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Список заказов с поиском, фильтрами и пагинацией."""
    permission_key = 'orders.view'
    model = Order
    template_name = 'orders/list.html'
    context_object_name = 'orders'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        if not can_view_orders(request.user):
            raise PermissionDenied('У вас нет доступа к просмотру заказов.')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = Order.objects.select_related(
            'client', 
            'service', 
            'created_by', 
            'assigned_manager'
        ).order_by('-scheduled_date', '-scheduled_time')
        
        user = self.request.user

        list_type = (self.request.GET.get('type') or 'active').strip().lower()
        if list_type not in ('active', 'success', 'canceled'):
            list_type = 'active'

        if list_type == 'success':
            queryset = queryset.filter(status=OrderStatus.COMPLETED)
        elif list_type == 'canceled':
            queryset = queryset.filter(status=OrderStatus.CANCELLED)
        else:
            queryset = queryset.exclude(status__in=[OrderStatus.COMPLETED, OrderStatus.CANCELLED])
        
        # MANAGER видит только переданные заказы или назначенные ему
        if self._is_manager(user) and not user.is_superuser:
            queryset = queryset.filter(
                Q(handed_to_manager=True) |
                Q(assigned_manager=user)
            )
        
        # CLEANER и SENIOR_CLEANER видят только заказы, где они назначены
        if hasattr(user, 'role') and user.role in ['CLEANER', 'SENIOR_CLEANER'] and not user.is_superuser:
            from apps.employees.models import Employee
            try:
                employee = Employee.objects.get(user=user)
                queryset = queryset.filter(order_employees__employee=employee)
            except Employee.DoesNotExist:
                queryset = queryset.none()
        
        # Поиск
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(order_code__icontains=search) |
                Q(client__first_name__icontains=search) |
                Q(client__last_name__icontains=search) |
                Q(client__phone__icontains=search)
            )
        
        # Фильтр по статусу
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Фильтр по услуге
        service = self.request.GET.get('service')
        if service:
            queryset = queryset.filter(service_id=service)
        
        # Фильтр по дате
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(scheduled_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(scheduled_date__lte=date_to)
        
        return queryset
    
    def _is_manager(self, user):
        """Проверка является ли пользователь менеджером, админом или суперадмином."""
        if hasattr(user, 'role'):
            return user.role in ['MANAGER', 'ADMIN', 'SUPER_ADMIN']
        return user.is_staff or user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_create_orders'] = can_create_orders(self.request.user)
        context['can_delete_orders'] = can_delete_orders(self.request.user)
        context['type_filter'] = (self.request.GET.get('type') or 'active').strip().lower() or 'active'
        context['search'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['service_filter'] = self.request.GET.get('service', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        context['status_choices'] = OrderStatus.choices
        from apps.services.models import Service
        context['services'] = Service.objects.filter(is_active=True)
        return context


class OrderCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Создание нового заказа."""
    permission_key = 'orders.create'
    model = Order
    form_class = OrderForm
    template_name = 'orders/form.html'
    success_url = reverse_lazy('orders_list')

    def _is_operator(self, user):
        """Проверка является ли пользователь оператором."""
        if hasattr(user, 'role'):
            return user.role in ['OPERATOR']
        return False

    def _is_manager(self, user):
        """Проверка является ли пользователь менеджером или админом."""
        if hasattr(user, 'role'):
            return user.role in ['MANAGER', 'ADMIN', 'SUPER_ADMIN']
        return user.is_staff or user.is_superuser
    
    def dispatch(self, request, *args, **kwargs):
        if not can_create_orders(request.user):
            raise PermissionDenied('У вас нет прав на создание заказов.')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_initial(self):
        """Предзаполнение клиента и категории заказа из GET-параметра."""
        initial = super().get_initial()
        client_id = self.request.GET.get('client')
        if client_id:
            initial['client'] = client_id
            # Определяем категорию заказа автоматически:
            # если у клиента уже есть заказы — повторный, иначе — новый.
            has_previous_orders = Order.objects.filter(client_id=client_id).exists()
            initial['category'] = (
                Order.OrderCategory.REPEAT
                if has_previous_orders
                else Order.OrderCategory.NEW
            )
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание заказа'
        context['button_text'] = 'Создать заказ'
        context['is_create'] = True
        context['is_manager'] = self._is_manager(self.request.user)
        context['is_operator'] = self._is_operator(self.request.user)
        from apps.services.models import Service
        active_services = Service.objects.filter(is_active=True).only('id', 'price', 'is_extra_only')
        context['service_prices'] = {str(s.id): str(s.price) for s in active_services}
        context['service_extra_map'] = {str(s.id): s.is_extra_only for s in active_services}
        context['inventory_items'] = InventoryItem.objects.filter(is_active=True).select_related('category').order_by(
            'item_type', 'category__name', 'name'
        )
        context['inventory_usage_rows'] = []
        context['inventory_usage_prefilled'] = False
         
        # Date/time dropdown values
        import calendar
        now = timezone.now()
        context['current_month'] = now.month
        context['current_day'] = now.day
        context['current_hour'] = now.hour
        # Show only next 14 days from today (shorter list)
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        end_day = min(now.day + 14, days_in_month)
        context['days_range'] = range(now.day, end_day + 1)
        context['hours_range'] = range(8, 21)  # 8:00 - 20:00 working hours
        
        # Если клиент предзаполнен, добавляем его в контекст для отображения
        client_id = self.request.GET.get('client')
        if client_id:
            from apps.clients.models import Client
            try:
                context['selected_client'] = Client.objects.get(pk=client_id)
            except Client.DoesNotExist:
                pass
        # Массив активных доп. услуг для выбора оператором
        context['extra_services_available'] = ExtraService.objects.filter(is_active=True).order_by('name')
        context['order_extra_services'] = []  # при создании заказа пусто
        return context
    
    def form_valid(self, form):
        user = self.request.user
        form.instance.created_by = user

        response = super().form_valid(form)
        
        # 0. Синхронизация доп. услуг
        sync_order_extra_services(self.object, self.request)
        
        # 1. Отправляем уведомление о создании заказа (всегда)
        try:
            NotificationService.new_order(self.object)
        except Exception as e:
            logger.error(f"Error sending new order notification: {e}")

        # 2. Автоматическая передача менеджеру, если создатель - оператор
        if self._is_operator(user):
            try:
                OrderStatusService.transfer_to_manager(self.object, user)
            except Exception as e:
                logger.error(f"Error in automatic order transfer: {e}")
        
        return response

    def form_invalid(self, form):
        logger.warning("OrderCreateView form_invalid errors=%s", form.errors)
        for field, errors in form.errors.items():
            if field == '__all__':
                for err in errors:
                    messages.error(self.request, str(err))
                continue
            label = form.fields.get(field).label if field in form.fields else field
            for err in errors:
                messages.error(self.request, f"{label}: {err}")
        return super().form_invalid(form)
    
    def _is_manager(self, user):
        """Проверка является ли пользователь менеджером или админом."""
        if hasattr(user, 'role'):
            return user.role in ['MANAGER', 'ADMIN', 'SUPER_ADMIN']
        return user.is_staff or user.is_superuser


class OrderDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Детальная страница заказа."""
    permission_key = 'orders.view'
    model = Order
    template_name = 'orders/detail.html'
    context_object_name = 'order'
    
    def dispatch(self, request, *args, **kwargs):
        if not can_view_orders(request.user):
            raise PermissionDenied('У вас нет доступа к просмотру заказов.')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        return super().get_queryset().select_related('client', 'service')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        order = self.object
        
        # Can transfer to manager: OPERATOR, FOUNDER, SUPER_ADMIN
        context['can_transfer_to_manager'] = self._can_transfer(user)
        
        # Can edit order: based on permissions
        context['can_edit_order'] = can_edit_orders(user)
        
        # Status actions for different roles
        context['operator_actions'] = OrderStatusChecker.get_operator_actions(order, user)
        context['manager_actions'] = OrderStatusChecker.get_manager_actions(order, user)
        context['senior_actions'] = OrderStatusChecker.get_senior_actions(order, user)
        
        # Helper properties for status display
        context['order_status_display'] = order.get_status_display()
        context['operator_status_display'] = order.get_operator_status_display()
        context['manager_status_display'] = order.get_manager_status_display()
        context['senior_cleaner_status_display'] = order.get_senior_cleaner_status_display()
        
        # Employees for "Move to Process" modal - берем из Пользователей по роли
        from apps.accounts.models import User
        context['senior_cleaners'] = User.objects.filter(
            role='SENIOR_CLEANER'
        ).select_related('employee')
        context['cleaners'] = User.objects.filter(
            role='CLEANER'
        ).select_related('employee')
        context['trainees'] = User.objects.filter(
            role='TRAINEE'
        ).select_related('employee')

        # Assigned employees and notes (for display)
        senior_assignment = order.order_employees.select_related('employee__user').filter(
            role_on_order='senior_cleaner',
            finished_at__isnull=True
        ).first()
        context['assigned_senior_cleaner'] = senior_assignment
        context['assigned_cleaners'] = order.order_employees.select_related('employee__user').filter(
            role_on_order='cleaner',
            finished_at__isnull=True
        )
        context['assigned_cleaner_ids'] = list(
            context['assigned_cleaners'].values_list('employee_id', flat=True)
        )
        context['assigned_cleaner_user_ids'] = list(
            context['assigned_cleaners'].values_list('employee__user_id', flat=True)
        )
        
        # Назначенные стажеры
        context['assigned_trainees'] = order.order_employees.select_related('employee__user').filter(
            role_on_order='trainee',
            finished_at__isnull=True
        )
        context['assigned_trainee_ids'] = list(
            context['assigned_trainees'].values_list('employee__user_id', flat=True)
        )
        context['notes_for_cleaners'] = (senior_assignment.notes if senior_assignment else '')
        context['inventory_usages'] = order.inventory_usages.select_related(
            'inventory_item', 'inventory_item__category'
        ).order_by('inventory_item__item_type', 'inventory_item__category__name', 'inventory_item__name')
        
        # Фактическое время выполнения работы
        if senior_assignment and senior_assignment.started_at and senior_assignment.finished_at:
            duration = senior_assignment.finished_at - senior_assignment.started_at
            context['actual_work_hours'] = round(duration.total_seconds() / 3600, 2)
        else:
            context['actual_work_hours'] = None
        
        # Task counters for checklist
        # Убедимся, что задачи сгенерированы (если заказ в процессе или дальше)
        if order.manager_status in ['PROCESS', 'REVIEW', 'DELIVERED']:
            try:
                from apps.tasks.services import TaskChecklistService
                TaskChecklistService.generate_order_tasks(order)
            except Exception:
                pass

        all_tasks_qs = order.tasks.prefetch_related('assigned_employees', 'assigned_employees__user').order_by('order_position', 'id')
        context['all_order_employees'] = order.order_employees.select_related('employee__user').filter(
            finished_at__isnull=True
        )
        context['extra_tasks_list'] = all_tasks_qs.filter(order_position__gte=100000)
        context['tasks_list'] = all_tasks_qs.filter(order_position__lt=100000)
        
        # Группируем задачи по комнатам для отображения
        tasks_by_room = {}
        for t in context['tasks_list']:
            room_name = "Общее"
            if t.description and t.description.startswith("Комната: "):
                room_name = t.description.replace("Комната: ", "")
            
            if room_name not in tasks_by_room:
                tasks_by_room[room_name] = []
            tasks_by_room[room_name].append(t)
        context['tasks_by_room'] = tasks_by_room

        context['order_copy_text'] = _build_order_copy_text(order)
        context['order_extra_services'] = order.order_extra_services.select_related('extra_service').all()
        
        return context
    
    def _can_transfer(self, user):
        """Проверка: может ли пользователь передать заказ менеджеру."""
        if user.is_superuser:
            return True
        if hasattr(user, 'role'):
            return user.role in ['OPERATOR', 'FOUNDER', 'SUPER_ADMIN']
        return False


class OrderUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Редактирование заказа."""
    permission_key = 'orders.edit'
    model = Order
    form_class = OrderForm
    template_name = 'orders/form.html'
    
    def get_success_url(self):
        """Redirect to order detail for managers, order list for operators."""
        if self._is_manager(self.request.user):
            return reverse('order_detail', kwargs={'pk': self.object.pk})
        return reverse('orders_list')
    
    def dispatch(self, request, *args, **kwargs):
        if not can_edit_orders(request.user):
            raise PermissionDenied('У вас нет прав на редактирование заказов.')
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Редактирование заказа'
        context['button_text'] = 'Сохранить'
        context['is_manager'] = self._is_manager(self.request.user)
        context['is_operator'] = self._is_operator(self.request.user)
        from apps.services.models import Service
        context['service_prices'] = {
            str(service.id): str(service.price)
            for service in Service.objects.filter(is_active=True).only('id', 'price')
        }
        context['inventory_items'] = InventoryItem.objects.filter(is_active=True).select_related('category').order_by(
            'item_type', 'category__name', 'name'
        )
        
        # Данные для менеджера: клинеры, старшие клинеры, назначения
        order = self.get_object()
        from apps.employees.models import Employee
        from apps.accounts.models import User
        from apps.tasks.models import OrderTask

        # Текущий назначенный старший клинер
        assigned_senior = order.order_employees.filter(
            role_on_order='senior_cleaner',
            finished_at__isnull=True
        ).first()
        context['assigned_senior_cleaner'] = assigned_senior

        # Текущие назначенные клинеры
        assigned_cleaners = order.order_employees.filter(
            role_on_order='cleaner',
            finished_at__isnull=True
        )
        context['assigned_cleaners'] = assigned_cleaners
        context['assigned_cleaner_ids'] = [ac.employee.user_id for ac in assigned_cleaners]

        # Список старших клинеров: только пользователи с ролью SENIOR_CLEANER
        senior_cleaner_users = User.objects.filter(
            role='SENIOR_CLEANER',
            is_active=True,
        ).distinct()
        context['senior_cleaners'] = senior_cleaner_users
        
        # Список обычных клинеров: только пользователи с ролью CLEANER
        cleaner_users = User.objects.filter(
            role='CLEANER',
            is_active=True,
        ).distinct()
        context['cleaners'] = cleaner_users
        
        # Список стажеров: только пользователи с ролью TRAINEE
        trainee_users = User.objects.filter(
            role='TRAINEE',
            is_active=True,
        ).distinct()
        context['trainees'] = trainee_users
        
        # Текущие назначенные стажеры
        assigned_trainees = order.order_employees.filter(
            role_on_order='trainee',
            finished_at__isnull=True
        )
        context['assigned_trainees'] = assigned_trainees
        context['assigned_trainee_ids'] = [at.employee.user_id for at in assigned_trainees]
        
        # Комментарий для клинеров (из заметок старшего клинера)
        if assigned_senior:
            context['notes_for_cleaners'] = assigned_senior.notes or ''
        else:
            context['notes_for_cleaners'] = ''

        inventory_rows, inventory_prefilled = build_inventory_usage_initial(order)
        context['inventory_usage_rows'] = inventory_rows
        context['inventory_usage_prefilled'] = inventory_prefilled
        # Данные об услугах для JS (цена и флаг is_extra_only)
        from apps.services.models import Service as SvcModel
        active_services = SvcModel.objects.filter(is_active=True).only('id', 'price', 'is_extra_only')
        context['service_prices'] = {str(s.id): str(s.price) for s in active_services}
        context['service_extra_map'] = {str(s.id): s.is_extra_only for s in active_services}
        
        # Дополнительные задачи (extra_tasks)
        context['extra_tasks'] = OrderTask.objects.filter(
            order=order,
            order_position__gte=100000  # Доп. задачи имеют позиции >= 100000
        ).order_by('order_position')
        
        # Доп. услуги: список доступных и уже прикреплённых к заказу
        context['extra_services_available'] = ExtraService.objects.filter(is_active=True).order_by('name')
        context['order_extra_services'] = order.order_extra_services.select_related('extra_service').all()
        
        return context
    
    def form_valid(self, form):
        """Обработка сохранения формы с дополнительными полями менеджера."""
        response = super().form_valid(form)
        
        # Обрабатываем поля менеджера только если пользователь - менеджер
        if self._is_manager(self.request.user):
            order = self.object
            
            # Получаем данные из POST
            senior_cleaner_id = self.request.POST.get('senior_cleaner')
            cleaners_ids = self.request.POST.getlist('cleaners')
            trainees_ids = self.request.POST.getlist('trainees')
            notes_for_cleaners = self.request.POST.get('notes_for_cleaners', '')
            extra_task_titles = self.request.POST.getlist('extra_task_title')
            extra_task_rooms = self.request.POST.getlist('extra_task_room')
            
            from apps.employees.models import Employee
            from apps.accounts.models import User
            from apps.tasks.models import OrderTask, OrderTaskStatus
            from decimal import Decimal, InvalidOperation
            
            def get_or_create_employee_from_user(user_id):
                """Получает или создает Employee по user_id."""
                try:
                    return Employee.objects.get(user_id=user_id)
                except Employee.DoesNotExist:
                    user = User.objects.get(pk=user_id)
                    employee = Employee.objects.create(
                        user=user,
                        status='ACTIVE',
                        employee_code=None
                    )
                    return employee
            
            # Назначаем старшего клинера (если выбран)
            if senior_cleaner_id:
                try:
                    senior_cleaner = get_or_create_employee_from_user(senior_cleaner_id)
                    
                    # Удаляем предыдущего старшего клинера (если меняли)
                    order.order_employees.filter(
                        role_on_order='senior_cleaner'
                    ).exclude(employee=senior_cleaner).delete()
                    
                    # Создаем/обновляем запись старшего клинера и сохраняем заметку
                    OrderEmployee.objects.update_or_create(
                        order=order,
                        employee=senior_cleaner,
                        defaults={
                            'role_on_order': 'senior_cleaner',
                            'notes': notes_for_cleaners,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Could not assign senior cleaner {senior_cleaner_id}: {e}")
            else:
                # Если старшего клинера сняли с заказа
                order.order_employees.filter(role_on_order='senior_cleaner').delete()
            
            # Назначаем обычных клинеров
            selected_cleaners = []
            for cleaner_id in cleaners_ids:
                try:
                    cleaner = get_or_create_employee_from_user(cleaner_id)
                    selected_cleaners.append(cleaner.pk)
                    OrderEmployee.objects.update_or_create(
                        order=order,
                        employee=cleaner,
                        defaults={'role_on_order': 'cleaner'}
                    )
                except Exception as e:
                    logger.warning(f"Could not assign cleaner {cleaner_id}: {e}")
                    continue
            
            # Удаляем клинеров, которых сняли
            if selected_cleaners:
                order.order_employees.filter(
                    role_on_order='cleaner'
                ).exclude(employee_id__in=selected_cleaners).delete()
            else:
                order.order_employees.filter(role_on_order='cleaner').delete()
            
            # Назначаем стажеров
            selected_trainees = []
            for trainee_id in trainees_ids:
                try:
                    trainee = get_or_create_employee_from_user(trainee_id)
                    selected_trainees.append(trainee.pk)
                    OrderEmployee.objects.update_or_create(
                        order=order,
                        employee=trainee,
                        defaults={'role_on_order': 'trainee'}
                    )
                except Exception as e:
                    logger.warning(f"Could not assign trainee {trainee_id}: {e}")
                    continue
            
            # Удаляем стажеров, которых сняли
            if selected_trainees:
                order.order_employees.filter(
                    role_on_order='trainee'
                ).exclude(employee_id__in=selected_trainees).delete()
            else:
                order.order_employees.filter(role_on_order='trainee').delete()
            
            # Обновляем доп. задачи: удаляем старые и создаем новые
            if extra_task_titles:
                # Удаляем существующие доп. задачи
                OrderTask.objects.filter(
                    order=order,
                    order_position__gte=100000
                ).delete()
                
                # Создаем новые доп. задачи
                base_pos = 100000
                for idx, raw_title in enumerate(extra_task_titles):
                    title = (raw_title or '').strip()
                    if not title:
                        continue
                    
                    room = ''
                    if idx < len(extra_task_rooms):
                        room = (extra_task_rooms[idx] or '').strip()
                    
                    description = f"Комната: {room}" if room else ''
                    OrderTask.objects.create(
                        order=order,
                        title=title,
                        description=description,
                        order_position=base_pos + idx + 1,
                        status=OrderTaskStatus.PENDING,
                    )

            sync_order_inventory_usage(order, self.request)
        
        # Синхронизация доп. услуг доступна для всех ролей (оператор, менеджер, основатель)
        sync_order_extra_services(self.object, self.request)
        
        return response
    
    def _is_operator(self, user):
        """Проверка является ли пользователь оператором."""
        if hasattr(user, 'role'):
            return user.role in ['OPERATOR']
        return False

    def _is_manager(self, user):
        """Проверка является ли пользователь менеджером или админом."""
        if hasattr(user, 'role'):
            return user.role in ['MANAGER', 'ADMIN', 'SUPER_ADMIN']
        return user.is_staff or user.is_superuser


class OrderDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Удаление заказа."""
    permission_key = 'orders.delete'
    model = Order
    template_name = 'orders/delete.html'
    success_url = reverse_lazy('orders_list')
    context_object_name = 'order'
    
    def dispatch(self, request, *args, **kwargs):
        if not can_delete_orders(request.user):
            raise PermissionDenied('У вас нет прав на удаление заказов.')
        return super().dispatch(request, *args, **kwargs)


class OrderHandToManagerView(LoginRequiredMixin, View):
    """Предать заказ менеджеру."""
    
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        
        # Проверка прав
        if not can_edit_orders(request.user):
            raise PermissionDenied('У вас нет прав на редактирование заказов.')
        
        # Устанавливаем флаг и дату передачи
        order.handed_to_manager = True
        order.handed_to_manager_at = timezone.now()
        order.save()
        
        messages.success(request, 'Заказ успешно передан менеджеру.')
        return redirect('order_detail', pk=order.pk)


class OrderTransferToManagerView(LoginRequiredMixin, View):
    """Передать заказ оператором менеджеру для обработки."""
    
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        
        try:
            OrderStatusService.transfer_to_manager(order, request.user)
            messages.success(
                request, 
                f'Заказ #{order.pk} успешно передан менеджеру. Менеджер теперь может работать с заказом.'
            )
        except PermissionDenied as e:
            messages.error(request, str(e))
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('order_detail', pk=order.pk)


class OrderRejectByOperatorView(LoginRequiredMixin, View):
    """Оператор отменяет заказ."""
    
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        reason = request.POST.get('reason', '')
        
        try:
            OrderStatusService.reject_by_operator(order, request.user, reason)
            messages.success(request, f'Заказ #{order.pk} отклонён.')
        except PermissionDenied as e:
            messages.error(request, str(e))
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('order_detail', pk=order.pk)


class OrderConfirmSuccessView(LoginRequiredMixin, View):
    """Оператор подтверждает успешное завершение заказа."""
    
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        
        try:
            OrderStatusService.operator_mark_success(order, request.user)
            messages.success(request, f'Заказ #{order.pk} успешно завершён!')
        except PermissionDenied as e:
            messages.error(request, str(e))
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('order_detail', pk=order.pk)


class ManagerAcceptOrderView(LoginRequiredMixin, View):
    """Менеджер принимает заказ в работу."""
    
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        
        try:
            OrderStatusService.manager_accept(order, request.user)
            messages.success(request, f'Заказ #{order.pk} принят в работу.')
        except PermissionDenied as e:
            messages.error(request, str(e))
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('order_detail', pk=order.pk)


class ManagerMoveToProcessView(LoginRequiredMixin, View):
    """Менеджер переводит заказ в процесс с назначением клинеров."""
    
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        
        # DEBUG: логируем что пришло
        logger.info(f"[DEBUG] ManagerMoveToProcessView: user={request.user}, role={getattr(request.user, 'role', 'NO ROLE')}")
        logger.info(f"[DEBUG] POST data: senior_cleaner={request.POST.get('senior_cleaner')}, cleaners={request.POST.getlist('cleaners')}, notes={request.POST.get('notes_for_cleaners', '')[:50]}")
        
        # Получаем данные из формы
        final_price = request.POST.get('final_price')
        senior_cleaner_id = request.POST.get('senior_cleaner')
        cleaners_ids = request.POST.getlist('cleaners')
        trainees_ids = request.POST.getlist('trainees')
        notes_for_cleaners = request.POST.get('notes_for_cleaners', '')
        extra_task_titles = request.POST.getlist('extra_task_title')
        extra_task_rooms = request.POST.getlist('extra_task_room')
        
        try:
            with transaction.atomic():
                # Обновляем цену если указана
                if final_price:
                    try:
                        order.price = Decimal(final_price)
                        order.save(update_fields=['price'])
                    except (ValueError, InvalidOperation):
                        pass

                # Назначаем старшего клинера (обязательно)
                # Старший клинер НЕ обязателен: заказ можно перевести в процесс без назначений.

                from apps.employees.models import Employee
                from apps.accounts.models import User
                
                def get_or_create_employee_from_user(user_id):
                    """Получает или создает Employee по user_id."""
                    try:
                        return Employee.objects.get(user_id=user_id)
                    except Employee.DoesNotExist:
                        # Создаем Employee для пользователя
                        user = User.objects.get(pk=user_id)
                        employee = Employee.objects.create(
                            user=user,
                            status='ACTIVE',
                            employee_code=None
                        )
                        return employee
                
                if senior_cleaner_id:
                    senior_cleaner = get_or_create_employee_from_user(senior_cleaner_id)

                    # Удаляем предыдущего старшего клинера (если меняли)
                    order.order_employees.filter(
                        role_on_order='senior_cleaner'
                    ).exclude(employee=senior_cleaner).delete()

                    # Создаем/обновляем запись старшего клинера и сохраняем заметку
                    OrderEmployee.objects.update_or_create(
                        order=order,
                        employee=senior_cleaner,
                        defaults={
                            'role_on_order': 'senior_cleaner',
                            'notes': notes_for_cleaners,
                        }
                    )
                else:
                    # Если старшего клинера не выбрали — сохраняем заметку как есть (не привязывая к сотруднику)
                    # и не блокируем перевод заказа в процесс.
                    pass

                # Назначаем обычных клинеров
                selected_cleaners = []
                for cleaner_id in cleaners_ids:
                    try:
                        cleaner = get_or_create_employee_from_user(cleaner_id)
                        selected_cleaners.append(cleaner.pk)
                        OrderEmployee.objects.update_or_create(
                            order=order,
                            employee=cleaner,
                            defaults={'role_on_order': 'cleaner'}
                        )
                    except Exception as e:
                        logger.warning(f"Could not assign cleaner {cleaner_id}: {e}")
                        continue

                # Удаляем клинеров, которых сняли
                if selected_cleaners:
                    order.order_employees.filter(
                        role_on_order='cleaner'
                    ).exclude(employee_id__in=selected_cleaners).delete()
                else:
                    order.order_employees.filter(role_on_order='cleaner').delete()

                # Назначаем стажеров
                selected_trainees = []
                for trainee_id in trainees_ids:
                    try:
                        trainee = get_or_create_employee_from_user(trainee_id)
                        selected_trainees.append(trainee.pk)
                        OrderEmployee.objects.update_or_create(
                            order=order,
                            employee=trainee,
                            defaults={'role_on_order': 'trainee'}
                        )
                    except Exception as e:
                        logger.warning(f"Could not assign trainee {trainee_id}: {e}")
                        continue

                # Удаляем стажеров, которых сняли
                if selected_trainees:
                    order.order_employees.filter(
                        role_on_order='trainee'
                    ).exclude(employee_id__in=selected_trainees).delete()
                else:
                    order.order_employees.filter(role_on_order='trainee').delete()

                # Доп. задачи (создаем как OrderTask)
                if extra_task_titles:
                    from apps.tasks.models import OrderTask, OrderTaskStatus

                    # Ставим доп. задачи в самый низ списка всегда (не зависит от текущих позиций)
                    base_pos = 100000

                    for idx, raw_title in enumerate(extra_task_titles):
                        title = (raw_title or '').strip()
                        if not title:
                            continue

                        room = ''
                        if idx < len(extra_task_rooms):
                            room = (extra_task_rooms[idx] or '').strip()

                        description = f"Комната: {room}" if room else ''
                        OrderTask.objects.create(
                            order=order,
                            title=title,
                            description=description,
                            order_position=base_pos + idx + 1,
                            status=OrderTaskStatus.PENDING,
                        )

                OrderStatusService.manager_move_to_process(order, request.user)

            # Дополнительная защита: фиксируем статус менеджера,
            # чтобы кнопка "Перевести в процесс" не появлялась повторно.
            if order.manager_status != Order.ManagerStatus.PROCESS:
                order.manager_status = Order.ManagerStatus.PROCESS
                order.save(update_fields=['manager_status'])
            messages.success(request, f'Заказ #{order.pk} переведён в процесс и клинеры назначены.')

            # Детальное уведомление в Telegram (тема «Уведомления»)
            try:
                from apps.notifications.services.telegram_service import TelegramService
                order.refresh_from_db()
                senior_oe = order.order_employees.filter(
                    role_on_order='senior_cleaner',
                    finished_at__isnull=True
                ).select_related('employee__user').first()
                cleaner_oes = order.order_employees.filter(
                    role_on_order='cleaner',
                    finished_at__isnull=True
                ).select_related('employee__user')
                senior_name = senior_oe.employee.user.full_name if senior_oe and senior_oe.employee else '—'
                cleaner_names = ', '.join(
                    oe.employee.user.full_name for oe in cleaner_oes if oe.employee and oe.employee.user
                ) or '—'
                price_str = f"{order.price} сом" if order.price else '—'
                sched_date = order.scheduled_date.strftime('%d.%m.%Y') if order.scheduled_date else '—'
                sched_time = order.scheduled_time.strftime('%H:%M') if order.scheduled_time else ''
                manager_name = getattr(request.user, 'full_name', '') or getattr(request.user, 'phone', str(request.user))
                text = (
                    f"🧹 <b>Заказ отправлен в работу</b>\n\n"
                    f"📋 Заказ: <b>{order.order_code}</b>\n"
                    f"🛁 Услуга: {order.service.name if order.service else '—'}\n"
                    f"👤 Клиент: {order.client.get_full_name() if order.client else '—'}\n"
                    f"📍 Адрес: {order.address or '—'}\n"
                    f"📅 Дата: {sched_date} {sched_time}\n\n"
                    f"⭐ Ст. клинер: {senior_name}\n"
                    f"👥 Клинеры: {cleaner_names}\n"
                    f"💰 Итоговая цена: {price_str}\n\n"
                    f"👨‍💼 Менеджер: {manager_name}"
                )
                TelegramService().send_cleaner_message(text)
            except Exception:
                pass

        except PermissionDenied as e:
            messages.error(request, str(e))
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.exception('ManagerMoveToProcessView failed for order_id=%s', order.pk)
            messages.error(
                request,
                f'Не удалось перевести заказ в процесс: {e}'
            )
        
        return redirect('order_detail', pk=order.pk)


class ManagerMarkDeliveredView(LoginRequiredMixin, View):
    """Менеджер сдаёт проект."""
    
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        
        try:
            OrderStatusService.manager_mark_delivered(order, request.user)
            messages.success(request, f'Заказ #{order.pk} сдан!')
        except PermissionDenied as e:
            messages.error(request, str(e))
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('order_detail', pk=order.pk)


class SeniorAcceptOrderView(LoginRequiredMixin, View):
    """Старший клинер принимает заказ."""
    
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        
        try:
            OrderStatusService.senior_accept(order, request.user)
            messages.success(request, f'Заказ #{order.pk} принят.')
        except PermissionDenied as e:
            messages.error(request, str(e))
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('order_detail', pk=order.pk)


class SeniorStartWorkView(LoginRequiredMixin, View):
    """Старший клинер начинает работу."""
    
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        
        try:
            OrderStatusService.senior_start_work(order, request.user)
            messages.success(request, f'Заказ #{order.pk} в работе.')
        except PermissionDenied as e:
            messages.error(request, str(e))
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('order_detail', pk=order.pk)


class SeniorSendForReviewView(LoginRequiredMixin, View):
    """Старший клинер отправляет заказ на проверку."""
    
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        
        try:
            OrderStatusService.senior_send_for_review(order, request.user)
            messages.success(request, f'Заказ #{order.pk} отправлен на проверку менеджеру.')
        except PermissionDenied as e:
            messages.error(request, str(e))
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('order_detail', pk=order.pk)


class OrderResendNotificationView(LoginRequiredMixin, View):
    """Повторная отправка уведомления о заказе в Telegram."""
    
    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        
        # Проверяем права (оператор, менеджер, админ)
        if not can_create_orders(request.user):
            raise PermissionDenied('У вас нет прав на отправку уведомлений.')
        
        try:
            NotificationService.new_order(order)
            messages.success(request, f'Уведомление о заказе {order.order_code} отправлено повторно.')
        except Exception as e:
            messages.error(request, f'Ошибка при отправке уведомления: {e}')
        
        return redirect('order_detail', pk=order.pk)
