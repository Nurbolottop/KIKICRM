from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("", views.order_list, name="order_list"),
    path("<int:pk>/", views.order_detail, name="order_detail"),
    path("create/", views.order_create, name="order_create"),
    path("<int:pk>/manager-edit/", views.order_update, name="order_manager_update"),
    path("<int:pk>/operator-edit/", views.order_operator_update, name="order_operator_update"),
    path("<int:pk>/send-to-manager/", views.order_send_to_manager, name="order_send_to_manager"),
    path("<int:pk>/start-work/", views.order_start_work, name="order_start_work"),
    path("<int:pk>/finish-work/", views.order_finish_work, name="order_finish_work"),
    path("<int:pk>/quality-check/", views.order_quality_check, name="order_quality_check"),
    path("<int:order_id>/task/create/", views.task_create, name="task_create"),
    path("task/<int:pk>/update/", views.task_update, name="task_update"),
    path("task/<int:pk>/delete/", views.task_delete, name="task_delete"),
]
