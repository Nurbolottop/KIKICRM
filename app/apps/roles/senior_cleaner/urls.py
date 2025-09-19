
from django.urls import path
from apps.roles.senior_cleaner import views as senior_cleaner_views

app_name = 'senior_cleaner'

urlpatterns = [
    path('', senior_cleaner_views.index, name='index'),
]