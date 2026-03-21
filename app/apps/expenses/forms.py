from django import forms
from .models import Expense


class ExpenseForm(forms.ModelForm):
    """Форма для создания и редактирования расхода."""
    
    class Meta:
        model = Expense
        fields = ['is_general', 'order', 'category', 'amount', 'description', 'photo']
        widgets = {
            'is_general': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Сумма в сомах', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Описание расхода'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Если это не общий расход, показать поле сотрудника
        if user and hasattr(user, 'employee'):
            self.fields['employee'].queryset = user.employee.__class__.objects.filter(
                status='ACTIVE'
            ).select_related('user')
            # По умолчанию выбираем текущего сотрудника
            if not self.instance.pk:
                self.fields['employee'].initial = user.employee
        
        # Фильтр заказов - только актуальные (за последние 30 дней, активные статусы)
        from django.utils import timezone
        from datetime import timedelta
        from apps.orders.models import Order
        
        thirty_days_ago = timezone.now() - timedelta(days=30)
        self.fields['order'].queryset = Order.objects.filter(
            status__in=['IN_WORK', 'ON_REVIEW', 'COMPLETED'],
            created_at__gte=thirty_days_ago
        ).order_by('-created_at')
        self.fields['order'].required = False
