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
from .models import Order, OrderEmployee, OrderInventoryUsage, OrderPhoto, RefuseSettings, OrderStatus
from .forms import OrderForm
from apps.orders.services.order_status_service import OrderStatusChecker, OrderStatusService
from apps.notifications.services.notification_service import NotificationService
from apps.inventory.models import InventoryItem, InventoryTransaction, TransactionType
from apps.services.models import ServiceInventoryTemplate


logger = logging.getLogger(__name__)


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
        context['service_prices'] = {
            str(service.id): str(service.price)
            for service in Service.objects.filter(is_active=True).only('id', 'price')
        }
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
        return context
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        # Отправляем уведомление в Telegram
        try:
            NotificationService.new_order(self.object)
        except Exception:
            pass  # Не блокируем создание заказа если Telegram недоступен
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
        # Доп. задачи создаются с высоким order_position (>= 100000) и отображаются отдельно
        all_tasks_qs = order.tasks.order_by('order_position', 'id')
        context['extra_tasks_list'] = all_tasks_qs.filter(order_position__gte=100000)
        context['tasks_list'] = all_tasks_qs.filter(order_position__lt=100000)  # Только обычные задачи
        context['tasks_total'] = context['tasks_list'].count()
        context['tasks_completed'] = context['tasks_list'].filter(
            status__in=['DONE', 'SKIPPED']
        ).count()
        
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
        
        # Комментарий для клинеров (из заметок старшего клинера)
        if assigned_senior:
            context['notes_for_cleaners'] = assigned_senior.notes or ''
        else:
            context['notes_for_cleaners'] = ''

        inventory_rows, inventory_prefilled = build_inventory_usage_initial(order)
        context['inventory_usage_rows'] = inventory_rows
        context['inventory_usage_prefilled'] = inventory_prefilled
        
        # Дополнительные задачи (extra_tasks)
        context['extra_tasks'] = OrderTask.objects.filter(
            order=order,
            order_position__gte=100000  # Доп. задачи имеют позиции >= 100000
        ).order_by('order_position')
        
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
                if not senior_cleaner_id:
                    raise ValueError('Выберите старшего клинера.')

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
