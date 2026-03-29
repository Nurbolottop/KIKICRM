from django.urls import path
from . import views


urlpatterns = [
    path('', views.reviews_list, name='reviews_list'),
    path('create/', views.review_create, name='review_create'),
    path('<int:pk>/', views.review_detail, name='review_detail'),
    path('<int:pk>/delete/', views.review_delete, name='review_delete'),
]
