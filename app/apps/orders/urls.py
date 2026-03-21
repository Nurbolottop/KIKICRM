from django.urls import path
from . import views

urlpatterns = [
    path('', views.OrderListView.as_view(), name='orders_list'),
    path('create/', views.OrderCreateView.as_view(), name='order_create'),
    path('<int:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('<int:pk>/edit/', views.OrderUpdateView.as_view(), name='order_update'),
    path('<int:pk>/delete/', views.OrderDeleteView.as_view(), name='order_delete'),
    
    # Status transition URLs
    path('<int:pk>/hand-to-manager/', views.OrderHandToManagerView.as_view(), name='order_hand_to_manager'),
    path('<int:pk>/transfer-to-manager/', views.OrderTransferToManagerView.as_view(), name='order_transfer_to_manager'),
    path('<int:pk>/reject/', views.OrderRejectByOperatorView.as_view(), name='order_reject'),
    path('<int:pk>/confirm-success/', views.OrderConfirmSuccessView.as_view(), name='order_confirm_success'),
    
    # Manager status URLs
    path('<int:pk>/manager-accept/', views.ManagerAcceptOrderView.as_view(), name='manager_accept'),
    path('<int:pk>/manager-process/', views.ManagerMoveToProcessView.as_view(), name='manager_process'),
    path('<int:pk>/manager-deliver/', views.ManagerMarkDeliveredView.as_view(), name='manager_deliver'),
    
    # Senior cleaner status URLs
    path('<int:pk>/senior-accept/', views.SeniorAcceptOrderView.as_view(), name='senior_accept'),
    path('<int:pk>/senior-start/', views.SeniorStartWorkView.as_view(), name='senior_start'),
    path('<int:pk>/senior-review/', views.SeniorSendForReviewView.as_view(), name='senior_review'),
]
