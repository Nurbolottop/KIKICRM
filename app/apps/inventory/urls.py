from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    # Остатки
    path("stock/", views.stock_list, name="stock_list"),
    
    # Товары
    path("products/", views.product_list, name="product_list"),
    path("products/add/", views.product_add, name="product_add"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    
    # Движения
    path("movements/incoming/", views.stock_incoming, name="stock_incoming"),
    path("movements/order-issue/", views.order_issue, name="order_issue"),
    path("movements/history/", views.movement_history, name="movement_history"),
    
    # Инвентаризация
    path("inventory-checks/", views.inventory_check_list, name="check_list"),
    path("inventory-checks/create/", views.inventory_check_create, name="check_create"),
    path("inventory-checks/<int:pk>/", views.inventory_check_detail, name="check_detail"),
    path("inventory-checks/<int:check_pk>/items/<int:item_pk>/update/", 
         views.inventory_check_item_update, name="check_item_update"),
    path("inventory-checks/<int:pk>/complete/", views.inventory_check_complete, name="check_complete"),
    
    # Списания
    path("write-offs/", views.write_off_list, name="writeoff_list"),
    path("write-offs/create/", views.write_off_create, name="writeoff_create"),
]
