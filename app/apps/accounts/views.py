from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from .forms import PhoneAuthenticationForm
from .models import UserRole


class PhoneLoginView(LoginView):
    """Кастомный view для входа с нормализацией телефона."""
    authentication_form = PhoneAuthenticationForm
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """Редирект в зависимости от роли пользователя."""
        user = self.request.user
        if user.role in [UserRole.CLEANER, UserRole.SENIOR_CLEANER]:
            return reverse_lazy('index_cl')
        return reverse_lazy('dashboard')
