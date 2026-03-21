"""
Формы для приложения Клиенты.
"""
from django import forms
from .models import Client


class ClientForm(forms.ModelForm):
    """Форма для создания и редактирования клиента."""

    class Meta:
        model = Client
        fields = [
            'photo',
            'last_name',
            'first_name',
            'middle_name',
            'organization',
            'category',
            'source',
            'gender',
            'phone',
            'phone_secondary',
            'whatsapp',
            'email',
            'birth_date',
            'address',
            'notes',
        ]
        widgets = {
            'photo': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control',
                    'accept': 'image/*',
                }
            ),
            'last_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Введите фамилию',
                }
            ),
            'first_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Введите имя',
                }
            ),
            'middle_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Введите отчество',
                }
            ),
            'organization': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Название организации',
                }
            ),
            'category': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),
            'source': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),
            'gender': forms.Select(
                attrs={
                    'class': 'form-select',
                }
            ),
            'phone': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': '+996 555 123 456',
                }
            ),
            'phone_secondary': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Дополнительный номер',
                }
            ),
            'whatsapp': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': '+996 555 123 456',
                }
            ),
            'email': forms.EmailInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'email@example.com',
                }
            ),
            'birth_date': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                }
            ),
            'address': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Введите адрес',
                }
            ),
            'notes': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Дополнительная информация о клиенте',
                    'rows': 4,
                }
            ),
        }
        labels = {
            'photo': 'Фотография',
            'last_name': 'Фамилия',
            'first_name': 'Имя',
            'middle_name': 'Отчество',
            'organization': 'Организация',
            'category': 'Категория',
            'source': 'Источник',
            'gender': 'Пол',
            'phone': 'Телефон',
            'phone_secondary': 'Дополнительный телефон',
            'whatsapp': 'WhatsApp',
            'email': 'Email',
            'birth_date': 'Дата рождения',
            'address': 'Адрес',
            'notes': 'Примечания',
        }
