"""
URLs для приложения задач (Task Checklist System).
"""
from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    # API endpoints для управления задачами
    path('api/task/<int:task_id>/assign/', views.assign_task_to_employee, name='assign_task'),
    path('api/task/<int:task_id>/start/', views.start_task, name='start_task'),
    path('api/task/<int:task_id>/complete/', views.complete_task, name='complete_task'),
    path('api/task/<int:task_id>/skip/', views.skip_task, name='skip_task'),
    path('api/task/<int:task_id>/reset/', views.reset_task, name='reset_task'),
    
    # API для статистики
    path('api/order/<int:order_id>/task-stats/', views.get_task_stats, name='order_task_stats'),
    
    path('my-tasks/', views.my_tasks, name='my_tasks'),
    
    # Массовое распределение задач
    path('order/<int:order_id>/tasks/distribute/', views.distribute_tasks_page, name='distribute_tasks'),
    path('order/<int:order_id>/tasks/bulk-assign/', views.bulk_assign_tasks, name='bulk_assign_tasks'),
]
