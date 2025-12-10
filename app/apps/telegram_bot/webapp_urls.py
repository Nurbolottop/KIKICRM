from django.urls import path
from . import webapp_views as views

app_name = "telegram_webapp"

urlpatterns = [
    path("app", views.app_home, name="app_home"),
    path("task/<int:pk>", views.task_page, name="task_page"),
    # API endpoints used by WebApp JS
    path("api/tasks", views.api_tasks, name="api_tasks"),
    path("api/task/<int:pk>/submit", views.api_task_submit, name="api_task_submit"),
]
