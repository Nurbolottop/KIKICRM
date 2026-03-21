from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Sum
from apps.common.permissions import PermissionRequiredMixin
from .models import InventoryCategory, InventoryItem, InventoryTransaction, TransactionType


class InventoryItemListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Список товаров на складе."""
    permission_key = 'inventory.view'
    model = InventoryItem
    template_name = 'inventory/item_list.html'
    context_object_name = 'items'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = InventoryItem.objects.select_related('category').order_by('category', 'name')
        
        # Поиск
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(category__name__icontains=search)
            )
        
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
        context['search'] = self.request.GET.get('search', '')
        context['category_filter'] = self.request.GET.get('category', '')
        context['low_stock_filter'] = self.request.GET.get('low_stock', '')
        context['categories'] = InventoryCategory.objects.filter(is_active=True)
        return context


class InventoryItemCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Создание нового товара."""
    permission_key = 'inventory.create'
    model = InventoryItem
    template_name = 'inventory/item_form.html'
    fields = ['name', 'category', 'unit', 'quantity', 'min_quantity', 'price_per_unit', 'is_active']
    success_url = reverse_lazy('inventory_list')
    
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
            'order', 'employee__user'
        ).order_by('-created_at')[:10]
        return context


class InventoryItemUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Редактирование товара."""
    permission_key = 'inventory.edit'
    model = InventoryItem
    template_name = 'inventory/item_form.html'
    fields = ['name', 'category', 'unit', 'min_quantity', 'price_per_unit', 'is_active']
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
            'item', 'item__category', 'order', 'employee__user'
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
    """Создание операции со складом."""
    permission_key = 'inventory.transactions'
    model = InventoryTransaction
    template_name = 'inventory/transaction_form.html'
    fields = ['item', 'transaction_type', 'quantity', 'order', 'employee', 'comment']
    success_url = reverse_lazy('inventory_transactions')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Новая операция'
        context['button_text'] = 'Создать'
        return context
