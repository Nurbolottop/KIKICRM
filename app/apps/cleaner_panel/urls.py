from django.urls import path
from . import views_cl, views
from .views_cancel_review import cancel_senior_review_cl

urlpatterns = [
    path('', views_cl.profile_cl, name='index_cl'),  # Профиль по умолчанию
    path('profile/', views_cl.profile_cl, name='profile_cl'),
    path('profile/edit/', views_cl.profile_edit_cl, name='profile_edit_cl'),
    path('orders/', views_cl.orders_cl, name='orders_cl'),
    path('orders/<int:order_id>/', views_cl.order_detail_cl, name='order_detail_cl'),
    path('orders/<int:order_id>/start/', views_cl.start_work_cl, name='start_work_cl'),
    path('orders/<int:order_id>/done/', views_cl.senior_done_cl, name='senior_done_cl'),
    path('orders/<int:order_id>/cancel-review/', cancel_senior_review_cl, name='cancel_senior_review_cl'),
    path('orders/<int:order_id>/tasks/bulk-assign/', views_cl.bulk_assign_tasks_cl, name='bulk_assign_tasks_cl'),
    path('orders/<int:order_id>/tasks/<int:task_id>/assign/', views_cl.assign_task_cl, name='assign_task_cl'),
    path('orders/<int:order_id>/tasks/<int:task_id>/complete/', views_cl.complete_task_cl, name='complete_task_cl'),
    path('orders/<int:order_id>/tasks/<int:task_id>/deadline/', views_cl.update_task_deadline_cl, name='update_task_deadline_cl'),
    path('orders/<int:order_id>/tasks/<int:task_id>/accept/', views_cl.accept_task_cl, name='accept_task_cl'),
    path('orders/<int:order_id>/tasks/<int:task_id>/rework/', views_cl.rework_task_cl, name='rework_task_cl'),
    # Expenses
    path('expenses/', views.expenses_cl, name='expenses_cl'),
    path('expenses/create/', views.expense_create_cl, name='expense_create_cl'),
]
