from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q, Count, Sum, ProtectedError
from django.utils import timezone
from django.http import JsonResponse
from django.views import View
from datetime import timedelta
from .models import Client, ClientNote
from .forms import ClientForm


class ClientListView(LoginRequiredMixin, ListView):
    """Список клиентов с поиском и пагинацией."""
    model = Client
    template_name = 'clients/list.html'
    context_object_name = 'clients'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        search = self.request.GET.get('q') or self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(phone__icontains=search)
            )

        profile_status = (self.request.GET.get('profile_status') or '').strip()
        if profile_status == 'complete':
            queryset = queryset.exclude(
                Q(last_name='') |
                Q(middle_name='') |
                Q(email='') |
                Q(birth_date__isnull=True) |
                Q(address='')
            )
        elif profile_status == 'incomplete':
            queryset = queryset.filter(
                Q(last_name='') |
                Q(middle_name='') |
                Q(email='') |
                Q(birth_date__isnull=True) |
                Q(address='')
            )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.common.permissions import can_create_clients, can_delete_clients

        context['can_create_clients'] = can_create_clients(self.request.user)
        context['can_delete_clients'] = can_delete_clients(self.request.user)
        context['search'] = self.request.GET.get('q') or self.request.GET.get('search', '')
        context['profile_status_filter'] = self.request.GET.get('profile_status', '')
        base_qs = Client.objects.all()
        context['complete_count'] = sum(1 for client in base_qs if client.is_profile_complete)
        context['incomplete_count'] = sum(1 for client in base_qs if not client.is_profile_complete)
        return context


class ClientAddNoteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        text = (request.POST.get('text') or '').strip()
        if not text:
            return JsonResponse({'ok': False, 'error': 'empty'}, status=400)

        client = Client.objects.filter(pk=pk).first()
        if not client:
            return JsonResponse({'ok': False, 'error': 'not_found'}, status=404)

        note = ClientNote.objects.create(
            client=client,
            author=request.user,
            text=text,
        )

        author_name = request.user.get_full_name() if hasattr(request.user, 'get_full_name') else str(request.user)
        return JsonResponse(
            {
                'ok': True,
                'note': {
                    'author': author_name or str(request.user),
                    'date': note.created_at.isoformat(),
                    'text': note.text,
                },
            }
        )


from django.http import HttpResponseRedirect
from django.urls import reverse


class ClientCreateView(LoginRequiredMixin, CreateView):
    """Создание нового клиента."""
    model = Client
    form_class = ClientForm
    template_name = 'clients/form.html'
    success_url = reverse_lazy('clients_list')

    def dispatch(self, request, *args, **kwargs):
        # Только OPERATOR и FOUNDER могут создавать клиентов
        if not self._can_create(request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied('У вас нет прав на создание клиентов.')
        return super().dispatch(request, *args, **kwargs)

    def _can_create(self, user):
        # OPERATOR, FOUNDER и SUPER_ADMIN могут создавать
        if hasattr(user, 'role'):
            return user.role in ['OPERATOR', 'FOUNDER', 'SUPER_ADMIN']
        return user.is_superuser

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['form_mode'] = 'create'
        return kwargs

    def get_success_url(self):
        if self.request.GET.get('return_to_order') == '1':
            return f"{reverse('order_create')}?client={self.object.pk}"
        if 'save_and_add_another' in self.request.POST:
            return reverse('clients_create')
        return super().get_success_url()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Добавление нового клиента'
        context['button_text'] = 'Сохранить'
        context['is_create'] = True
        context['return_to_order'] = self.request.GET.get('return_to_order') == '1'
        return context


class ClientDetailView(LoginRequiredMixin, DetailView):
    """Детальная страница клиента."""
    model = Client
    template_name = 'clients/detail.html'
    context_object_name = 'client'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.object

        # Статистика клиента
        orders = client.orders.all()
        context['total_orders'] = orders.count()
        total_amount = orders.aggregate(total=Sum('price'))['total']
        context['total_amount'] = total_amount if total_amount else 0

        # Debug: выводим в консоль для проверки
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Client {client.id} stats: orders={context['total_orders']}, amount={context['total_amount']}")

        # Первый и последний заказ
        first_order = orders.order_by('created_at').first()
        last_order = orders.order_by('-created_at').first()
        context['first_order_date'] = first_order.created_at if first_order else None
        context['last_order_date'] = last_order.created_at if last_order else None

        # Список заказов
        context['orders'] = orders.order_by('-created_at')[:10]

        # Права на создание заказа (только OPERATOR/FOUNDER/SUPER_ADMIN, НЕ MANAGER)
        from ..common.permissions import can_create_orders, can_edit_clients
        context['can_create_orders'] = can_create_orders(self.request.user)
        context['can_edit_clients'] = can_edit_clients(self.request.user)

        # Комментарии/заметки
        notes = [
            {
                'date': client.created_at,
                'text': 'Клиент создан',
                'author': client.created_by,
            }
        ] if client.created_by else []

        notes.extend(
            {
                'date': note.created_at,
                'text': note.text,
                'author': note.author,
            }
            for note in client.notes_list.select_related('author').all()
        )

        context['notes_list'] = sorted(
            notes,
            key=lambda x: x['date'] or timezone.now(),
            reverse=True,
        )

        # История активности
        context['history'] = [
            {'date': client.created_at, 'action': 'Клиент создан', 'icon': 'user-plus'},
        ]

        return context


class ClientUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование клиента."""
    model = Client
    form_class = ClientForm
    template_name = 'clients/form.html'
    success_url = reverse_lazy('clients_list')

    def dispatch(self, request, *args, **kwargs):
        from apps.common.permissions import can_edit_clients
        from django.core.exceptions import PermissionDenied

        if not can_edit_clients(request.user):
            raise PermissionDenied('У вас нет прав на редактирование клиентов.')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Редактирование клиента'
        context['button_text'] = 'Сохранить'
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['form_mode'] = 'edit'
        return kwargs


class ClientDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление клиента."""
    model = Client
    template_name = 'clients/delete.html'
    success_url = reverse_lazy('clients_list')
    context_object_name = 'client'

    def dispatch(self, request, *args, **kwargs):
        from apps.common.permissions import can_delete_clients
        from django.core.exceptions import PermissionDenied

        if not can_delete_clients(request.user):
            raise PermissionDenied('У вас нет прав на удаление клиентов.')
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            self.object.delete()
            from django.contrib import messages
            messages.success(request, 'Клиент успешно удален.')
            return HttpResponseRedirect(self.success_url)
        except ProtectedError:
            from django.contrib import messages
            messages.error(
                request,
                f'Невозможно удалить клиента "{self.object}" — у него есть связанные заказы.'
            )
            return HttpResponseRedirect(reverse('client_detail', kwargs={'pk': self.object.pk}))
