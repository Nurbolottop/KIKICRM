from django.urls import path
from . import views

urlpatterns = [
    path('hr/', views.hr_dashboard, name='hr_dashboard'),
    path('hr/employees/', views.hr_employees, name='hr_employees'),
    path('hr/employees/create/', views.hr_employee_create, name='hr_employee_create'),
    path('hr/employees/<int:pk>/', views.hr_employee_detail, name='hr_employee_detail'),
    path('hr/employees/<int:pk>/toggle-active/', views.hr_toggle_active, name='hr_toggle_active'),
    path('hr/employees/<int:pk>/edit/', views.hr_employee_edit, name='hr_employee_edit'),
    path('hr/employees/<int:pk>/dismiss/', views.hr_dismiss_employee, name='hr_dismiss_employee'),
    path('hr/employees/<int:pk>/promote/', views.hr_promote, name='hr_promote'),
    path('hr/settings/', views.hr_settings_view, name='hr_settings'),
    path('hr/logout/', views.hr_logout, name='hr_logout'),
]
