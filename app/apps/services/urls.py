from django.urls import path
from . import views

urlpatterns = [
    # ── Основные услуги ──────────────────────────────────────
    path('', views.ServiceListView.as_view(), name='services_list'),
    path('create/', views.ServiceCreateView.as_view(), name='service_create'),
    path('checklist-total-deadline/', views.ServiceChecklistTotalDeadlineView.as_view(), name='service_checklist_total_deadline'),
    path('<int:pk>/', views.ServiceDetailView.as_view(), name='service_detail'),
    path('<int:pk>/ajax-update/', views.ServiceAjaxUpdateView.as_view(), name='service_ajax_update'),
    path('<int:pk>/edit/', views.ServiceUpdateView.as_view(), name='service_update'),
    path('<int:pk>/delete/', views.ServiceDeleteView.as_view(), name='service_delete'),

    # ── Доп. услуги (прайс-лист) ─────────────────────────────
    path('extra/', views.ExtraServiceListView.as_view(), name='extra_services_list'),
    path('extra/create/', views.ExtraServiceCreateAjaxView.as_view(), name='extra_service_create'),
    path('extra/<int:pk>/update/', views.ExtraServiceUpdateAjaxView.as_view(), name='extra_service_update'),
    path('extra/<int:pk>/delete/', views.ExtraServiceDeleteView.as_view(), name='extra_service_delete'),
]
