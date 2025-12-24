from django.urls import path
from apps.users import views as users_views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('login/', users_views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('staff/', users_views.staff_list, name='staff_list'),
    path('staff/<int:pk>/', users_views.staff_detail, name='staff_detail'),
]
