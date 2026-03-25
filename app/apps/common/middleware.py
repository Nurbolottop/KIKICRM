"""Middleware для контроля доступа."""
from django.shortcuts import redirect
from django.urls import resolve
from apps.accounts.models import UserRole


class CleanerAccessMiddleware:
    """
    Middleware для блокировки доступа клинеров к CRM панели.
    Клинеры могут использовать только cleaner_panel.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Проверяем только для авторизованных пользователей
        if request.user.is_authenticated:
            # Проверяем, является ли пользователь клинером
            is_cleaner = request.user.role in [UserRole.CLEANER, UserRole.SENIOR_CLEANER]
            
            if is_cleaner:
                # Получаем текущий URL
                current_url = request.path
                
                # Разрешенные URL для клинеров
                allowed_urls = [
                    '/cleaner_panel/',
                    '/accounts/logout/',
                    '/static/',
                    '/media/',
                ]
                
                # Проверяем, начинается ли URL с разрешенного пути
                is_allowed = any(current_url.startswith(url) for url in allowed_urls)
                
                # Если URL не разрешен, перенаправляем на cleaner_panel
                if not is_allowed:
                    return redirect('profile_cl')
        
        response = self.get_response(request)
        return response
