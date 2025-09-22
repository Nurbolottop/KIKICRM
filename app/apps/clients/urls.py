
from django.urls import path
from apps.clients import views as clients_views

urlpatterns = [
    path('customer/', clients_views.customer_list, name='customer'),
    path('customer/add/', clients_views.customer_add, name='customer_add'),
    path('customer/views/<int:pk>/', clients_views.customer_view, name='customer_view'),
    path('customer/edit/<int:pk>/', clients_views.customer_edit, name='customer_edit'),
    path('customer/delete/<int:pk>/', clients_views.customer_delete, name='customer_delete'),
]