
from django.urls import path
from apps.roles.cleaner import views as cleaner_views

app_name = 'cleaner'

urlpatterns = [
    path('', cleaner_views.index, name='index'),
]