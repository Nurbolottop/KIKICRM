from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('admin/', admin.site.urls),

# приложения
    # login/logout → только в users
    path('users/', include('apps.users.urls')),
    # главная страница
    path('', include('apps.cms.urls')),
    # клиенты
    path('clients/', include('apps.clients.urls')),
    # заказы
    path('orders/', include(('apps.orders.urls', 'orders'), namespace='orders')),
    # Telegram Mini App (WebApp)
    path('tg/', include('apps.telegram_bot.webapp_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
