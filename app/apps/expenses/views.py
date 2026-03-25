from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from apps.common.permissions import PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .models import Expense
from .forms import ExpenseForm
from apps.telegram_bot.services.telegram_service import notify_new_expense, notify_expense_approved, notify_expense_rejected


class ExpenseListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Список расходов с поиском, фильтрами и пагинацией."""
    permission_key = 'expenses.view'
    model = Expense
    template_name = 'expenses/list.html'
    context_object_name = 'expenses'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Expense.objects.select_related('user', 'order').order_by('-created_at')
        
        # Основатель видит все расходы, остальные только свои
        if self.request.user.role != 'FOUNDER':
            queryset = queryset.filter(user=self.request.user)
        
        # Поиск по описанию
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(description__icontains=search)
        
        # Фильтр по категории
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Фильтр по заказу (только для основателя)
        order_id = self.request.GET.get('order')
        if order_id and self.request.user.role == 'FOUNDER':
            if order_id == 'none':
                queryset = queryset.filter(order__isnull=True)
            else:
                queryset = queryset.filter(order_id=order_id)
        
        # Фильтр по дате
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(expense_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(expense_date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['category_filter'] = self.request.GET.get('category', '')
        context['order_filter'] = self.request.GET.get('order', '')
        context['date_from'] = self.request.GET.get('date_from', '')
        context['date_to'] = self.request.GET.get('date_to', '')
        from .models import ExpenseCategory
        context['category_choices'] = ExpenseCategory.choices
        
        # Добавляем список заказов для основателя
        if self.request.user.role == 'FOUNDER':
            from apps.orders.models import Order
            context['orders'] = Order.objects.all().order_by('-created_at')[:100]
        
        return context


class ExpenseCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Создание нового расхода."""
    permission_key = 'expenses.create'
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/form.html'
    success_url = reverse_lazy('expenses_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Устанавливаем текущего пользователя автоматически
        form.instance.user = self.request.user
        
        response = super().form_valid(form)
        # Отправляем уведомление в Telegram
        try:
            notify_new_expense(self.object)
        except Exception:
            pass  # Не блокируем создание расхода если Telegram недоступен
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Новый расход'
        context['button_text'] = 'Создать'
        return context


class ExpenseDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Детальная страница расхода."""
    permission_key = 'expenses.view'
    model = Expense
    template_name = 'expenses/detail.html'
    context_object_name = 'expense'
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('user', 'order')
        
        # Основатель видит все расходы, остальные только свои
        if self.request.user.role != 'FOUNDER':
            queryset = queryset.filter(user=self.request.user)
        
        return queryset


class ExpenseUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Редактирование расхода."""
    permission_key = 'expenses.create'
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/form.html'
    success_url = reverse_lazy('expenses_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Редактирование расхода'
        context['button_text'] = 'Сохранить'
        context['expense'] = self.object  # Для отображения текущего фото
        return context


class ExpenseDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Удаление расхода."""
    permission_key = 'expenses.create'
    model = Expense
    template_name = 'expenses/delete.html'
    success_url = reverse_lazy('expenses_list')
    context_object_name = 'expense'
