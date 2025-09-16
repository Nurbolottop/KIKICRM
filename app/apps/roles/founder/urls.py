
from django.urls import path
from apps.roles.founder import views as founder_views

app_name = 'founder'

urlpatterns = [
    path('', founder_views.index, name='index'),
]