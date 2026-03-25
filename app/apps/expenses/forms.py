from django import forms
from .models import Expense, ExpenseCategory


class ExpenseForm(forms.ModelForm):
    """Форма для создания и редактирования расхода."""

    is_general = forms.BooleanField(
        required=False,
        label='Общий расход',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'role': 'switch',
        })
    )
    
    class Meta:
        model = Expense
        fields = ['order', 'category', 'amount', 'description', 'photo']
        widgets = {
            'order': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Сумма в сомах', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Описание расхода'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
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
        self.fields['category'].required = False

        if self.instance and self.instance.pk and not self.instance.order_id:
            self.fields['is_general'].initial = True
        else:
            self.fields['is_general'].initial = False

    def clean(self):
        cleaned_data = super().clean()
        is_general = cleaned_data.get('is_general')
        order = cleaned_data.get('order')
        category = cleaned_data.get('category')

        if is_general:
            cleaned_data['order'] = None
            cleaned_data['category'] = category or ExpenseCategory.OTHER
        elif not category:
            self.add_error('category', 'Выберите категорию расхода.')

        return cleaned_data
