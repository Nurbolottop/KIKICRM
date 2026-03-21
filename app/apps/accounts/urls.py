from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.PhoneLoginView.as_view(), name='login'),
]
