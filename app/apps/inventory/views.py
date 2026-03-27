from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Sum
from apps.common.permissions import PermissionRequiredMixin
from .models import InventoryCategory, InventoryItem, InventoryItemType, InventoryTransaction, TransactionType


class InventoryItemListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Список товаров на складе."""
    permission_key = 'inventory.view'
    model = InventoryItem
    template_name = 'inventory/item_list.html'
    context_object_name = 'items'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = InventoryItem.objects.select_related('category').order_by('item_type', 'category', 'name')
        
        # Поиск
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(category__name__icontains=search)
            )
        
        item_type = self.request.GET.get('item_type')
        if item_type:
            queryset = queryset.filter(item_type=item_type)
        
        # Фильтр по категории
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Фильтр по низкому остатку
        low_stock = self.request.GET.get('low_stock')
        if low_stock == 'yes':
            queryset = [item for item in queryset if item.is_low_stock()]
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        context['search'] = self.request.GET.get('search', '')
        context['category_filter'] = self.request.GET.get('category', '')
        context['item_type_filter'] = self.request.GET.get('item_type', '')
        context['low_stock_filter'] = self.request.GET.get('low_stock', '')
        context['categories'] = InventoryCategory.objects.filter(is_active=True)
        context['item_types'] = InventoryItemType.choices
        context['large_count'] = queryset.filter(item_type=InventoryItemType.LARGE).count() if hasattr(queryset, 'filter') else 0
        context['small_count'] = queryset.filter(item_type=InventoryItemType.SMALL).count() if hasattr(queryset, 'filter') else 0
        context['low_stock_count'] = sum(1 for item in queryset if item.is_low_stock())
        return context


class InventoryItemCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Создание нового товара."""
    permission_key = 'inventory.edit'
    model = InventoryItem
    template_name = 'inventory/item_form.html'
    fields = ['name', 'category', 'item_type', 'quantity', 'min_quantity', 'is_active']
    success_url = reverse_lazy('inventory_list')
    
    def form_valid(self, form):
        # Для крупного товара автоматически устанавливаем количество = 1
        if form.instance.item_type == InventoryItemType.LARGE:
            form.instance.quantity = 1
        response = super().form_valid(form)
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Новый товар'
        context['button_text'] = 'Создать'
        return context


class InventoryItemDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Детальная страница товара."""
    permission_key = 'inventory.view'
    model = InventoryItem
    template_name = 'inventory/item_detail.html'
    context_object_name = 'item'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Последние транзакции
        context['recent_transactions'] = self.object.transactions.select_related(
            'order', 'employee__user', 'usage'
        ).order_by('-created_at')[:10]
        return context


class InventoryItemUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Редактирование товара."""
    permission_key = 'inventory.edit'
    model = InventoryItem
    template_name = 'inventory/item_form.html'
    fields = ['name', 'category', 'item_type', 'min_quantity', 'is_active']
    success_url = reverse_lazy('inventory_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Редактирование товара'
        context['button_text'] = 'Сохранить'
        return context


class InventoryItemDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Удаление товара."""
    permission_key = 'inventory.edit'
    model = InventoryItem
    template_name = 'inventory/item_delete.html'
    success_url = reverse_lazy('inventory_list')
    context_object_name = 'item'


class InventoryTransactionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Список операций со складом."""
    permission_key = 'inventory.view'
    model = InventoryTransaction
    template_name = 'inventory/transaction_list.html'
    context_object_name = 'transactions'
    paginate_by = 30
    
    def get_queryset(self):
        queryset = InventoryTransaction.objects.select_related(
            'item', 'item__category', 'order', 'employee__user', 'usage'
        ).order_by('-created_at')
        
        # Фильтр по типу
        transaction_type = self.request.GET.get('type')
        if transaction_type:
            queryset = queryset.filter(transaction_type=transaction_type)
        
        # Фильтр по товару
        item = self.request.GET.get('item')
        if item:
            queryset = queryset.filter(item_id=item)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['type_filter'] = self.request.GET.get('type', '')
        context['item_filter'] = self.request.GET.get('item', '')
        context['transaction_types'] = TransactionType.choices
        context['items'] = InventoryItem.objects.filter(is_active=True).order_by('name')
        return context


class InventoryTransactionCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Создание операции со склада."""
    permission_key = 'inventory.transactions'
    model = InventoryTransaction
    template_name = 'inventory/transaction_form.html'
    fields = ['item', 'transaction_type', 'quantity', 'comment']
    success_url = reverse_lazy('inventory_transactions')
    
    def get_initial(self):
        """Автоматически выбираем товар из GET параметра item."""
        initial = super().get_initial()
        item_id = self.request.GET.get('item')
        if item_id:
            initial['item'] = item_id
        return initial
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Новая операция'
        context['button_text'] = 'Создать'
        
        # Если товар выбран (из GET или формы), показываем его детали
        item_id = self.request.GET.get('item') or self.request.POST.get('item')
        if item_id:
            try:
                context['selected_item'] = InventoryItem.objects.select_related('category').get(pk=item_id)
            except (InventoryItem.DoesNotExist, ValueError):
                pass
        
        return context
