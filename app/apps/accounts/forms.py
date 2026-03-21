from django.contrib.auth.forms import AuthenticationForm
from apps.common.utils.phone import normalize_phone


class PhoneAuthenticationForm(AuthenticationForm):
    """Кастомная форма аутентификации с нормализацией телефона."""
    
    def clean_username(self):
        """Нормализуем телефон при входе."""
        username = self.cleaned_data.get('username')
        if username:
            try:
                return normalize_phone(username)
            except ValueError:
                # Если нормализация не удалась, возвращаем как есть
                # Django покажет ошибку "Неверные учетные данные"
                return username
        return username
