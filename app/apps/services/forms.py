from django import forms
from .models import Service


class ServiceForm(forms.ModelForm):
    """Форма для создания и редактирования услуги."""
    
    class Meta:
        model = Service
        fields = ['name', 'description', 'image', 'price', 'room_count', 'senior_cleaner_salary', 'senior_cleaner_bonus', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Название услуги'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Описание услуги'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Цена в сомах',
                'step': '0.01'
            }),
            'room_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Количество комнат',
                'min': '1',
                'step': '1'
            }),
            'senior_cleaner_salary': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'ЗП ст. клинеру',
                'step': '0.01'
            }),
            'senior_cleaner_bonus': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Доп. оплата ст. клинеру',
                'step': '0.01'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _num_fields = ('price', 'room_count',
                       'senior_cleaner_salary', 'senior_cleaner_bonus')
        for fname in _num_fields:
            if fname not in self.fields:
                continue
            self.fields[fname].required = fname == 'price'
            # Полностью отключаем локализацию виджета —
            # Django 5 + LANGUAGE_CODE='ru' форматирует Decimal как '500,00'
            # (с запятой), что невалидно для <input type="number"> и браузер
            # показывает пустое поле.
            self.fields[fname].localize = False
            self.fields[fname].widget.is_localized = False
            # Принудительно конвертируем начальное значение в строку
            # через Python str() — он всегда использует точку, независимо от локали.
            if fname in self.initial and self.initial[fname] is not None:
                self.initial[fname] = str(self.initial[fname]).replace(',', '.')

    def clean_room_count(self):
        value = self.cleaned_data.get('room_count')
        if value in (None, ''):
            return 1
        return value

    def clean_senior_cleaner_salary(self):
        value = self.cleaned_data.get('senior_cleaner_salary')
        if value in (None, ''):
            return 0
        return value

    def clean_senior_cleaner_bonus(self):
        value = self.cleaned_data.get('senior_cleaner_bonus')
        if value in (None, ''):
            return 0
        return value

