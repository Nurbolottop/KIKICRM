from django.urls import path
from . import views

urlpatterns = [
    # Товары
    path('inventory/', views.InventoryItemListView.as_view(), name='inventory_list'),
    path('inventory/create/', views.InventoryItemCreateView.as_view(), name='inventory_create'),
    path('inventory/<int:pk>/', views.InventoryItemDetailView.as_view(), name='inventory_detail'),
    path('inventory/<int:pk>/edit/', views.InventoryItemUpdateView.as_view(), name='inventory_edit'),
    path('inventory/<int:pk>/delete/', views.InventoryItemDeleteView.as_view(), name='inventory_delete'),
    
    # Операции
    path('inventory/transactions/', views.InventoryTransactionListView.as_view(), name='inventory_transactions'),
    path('inventory/transactions/create/', views.InventoryTransactionCreateView.as_view(), name='inventory_transaction_create'),
]
