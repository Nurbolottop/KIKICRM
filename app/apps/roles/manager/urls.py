
from django.urls import path
from apps.roles.smm import views as smm_views

app_name = 'manager'

urlpatterns = [
    path('', smm_views.index, name='index'),
]