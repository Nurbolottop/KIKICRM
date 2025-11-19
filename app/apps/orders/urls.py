from django.urls import path
from . import views
from . import views_senior_cleaner

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
    
    # Старший клинер
    path("<int:pk>/senior-accept/", views_senior_cleaner.senior_cleaner_accept_order, name="senior_accept_order"),
    path("<int:pk>/senior-decline/", views_senior_cleaner.senior_cleaner_decline_order, name="senior_decline_order"),
    path("<int:pk>/senior-start/", views_senior_cleaner.senior_cleaner_start_work, name="senior_start_work"),
    path("<int:pk>/senior-finish/", views_senior_cleaner.senior_cleaner_finish_work, name="senior_finish_work"),
    path("task/<int:pk>/assign-cleaner/", views_senior_cleaner.task_assign_cleaner, name="task_assign_cleaner"),
]
