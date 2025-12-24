from django.urls import path
from apps.cms import views as cms_views

urlpatterns = [
    path('', cms_views.index, name='index'),
    path('services/', cms_views.services_list, name='services_list'),
    path('services/add/', cms_views.service_add, name='service_add'),
    path('services/<int:pk>/', cms_views.service_view, name='service_view'),
    path('services/<int:pk>/tasks/add/', cms_views.service_task_add, name='service_task_add'),
    path('services/<int:pk>/tasks/<int:task_id>/edit/', cms_views.service_task_edit, name='service_task_edit'),
    path('services/<int:pk>/tasks/<int:task_id>/delete/', cms_views.service_task_delete, name='service_task_delete'),
    path('services/<int:pk>/edit/', cms_views.service_edit, name='service_edit'),
    path('services/<int:pk>/delete/', cms_views.service_delete, name='service_delete'),
]
