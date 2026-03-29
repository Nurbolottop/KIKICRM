"""URL configuration for core project."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    
    # Auth
    path('accounts/', include('apps.accounts.urls')),  # Должно быть ПЕРЕД django.contrib.auth.urls
    path('accounts/', include('django.contrib.auth.urls')),
    
    # Dashboard
    path('', include('apps.dashboard.urls')),
    
    # CRM KIKI v2 endpoints
    path('clients/', include('apps.clients.urls')),
    path('orders/', include('apps.orders.urls')),
    path('services/', include('apps.services.urls')),
    path('expenses/', include('apps.expenses.urls')),
    path('', include('apps.inventory.urls')),
    path('', include('apps.common.urls')),
    path('', include('apps.employees.urls')),
    path('', include('apps.hr.urls')),
    path('', include('apps.tasks.urls')),
    path('', include('apps.notifications.urls')),
    path('', include('apps.reports.urls')),
    path('', include('apps.finance.urls')),
    path('cleaner_panel/', include('apps.cleaner_panel.urls')),
    path('', include('apps.telegram_bot.urls')),
    path('reviews/', include('apps.reviews.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)