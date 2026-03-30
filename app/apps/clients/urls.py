from django.urls import path
from . import views

urlpatterns = [
    path('', views.ClientListView.as_view(), name='clients_list'),
    path('create/', views.ClientCreateView.as_view(), name='clients_create'),
    path('<int:pk>/notes/add/', views.ClientAddNoteView.as_view(), name='clients_add_note'),
    path('<int:pk>/reviews/add/', views.ClientAddReviewView.as_view(), name='clients_add_review'),
    path('<int:pk>/', views.ClientDetailView.as_view(), name='clients_detail'),
    path('<int:pk>/edit/', views.ClientUpdateView.as_view(), name='clients_update'),
    path('<int:pk>/delete/', views.ClientDeleteView.as_view(), name='clients_delete'),
]
