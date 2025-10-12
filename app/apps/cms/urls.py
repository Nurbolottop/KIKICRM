from django.urls import path
from apps.cms import views as cms_views

urlpatterns = [
    path('', cms_views.index, name='index'),
]
