
from django.urls import path
from apps.roles.manager import views as manager_views

app_name = 'manager'

urlpatterns = [
    path('', manager_views.index, name='index'),
]