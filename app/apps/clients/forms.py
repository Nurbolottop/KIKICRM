"""
Формы для приложения Клиенты.
"""
from django import forms
from .models import Client


class ClientForm(forms.ModelForm):
    """Форма для создания и редактирования клиента."""

    def __init__(self, *args, **kwargs):
        form_mode = kwargs.pop('form_mode', 'edit')
        super().__init__(*args, **kwargs)

        if 'first_name' in self.fields:
            self.fields['first_name'].required = True
        if 'phone' in self.fields:
            self.fields['phone'].required = True

        if form_mode == 'create':
            hidden_fields = [
                'photo',
                'last_name',
                'middle_name',
                'category',
                'source',
                'email',
                'birth_date',
                'address',
            ]
            for name in hidden_fields:
                if name in self.fields:
                    self.fields[name].required = False
                    self.fields[name].widget = forms.HiddenInput()

            if 'category' in self.fields:
                self.fields['category'].initial = Client.ClientCategory.INDIVIDUAL
            if 'source' in self.fields:
                self.fields['source'].initial = Client.ClientSource.WEBSITE

    def clean_category(self):
        category = self.cleaned_data.get('category')
        organization = (self.cleaned_data.get('organization') or '').strip()
        if organization:
            return Client.ClientCategory.COMPANY
        return category or Client.ClientCategory.INDIVIDUAL

    def clean_source(self):
        return self.cleaned_data.get('source') or Client.ClientSource.WEBSITE

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


class ClientReviewForm(forms.ModelForm):
    """Форма для создания отзыва клиента."""

    class Meta:
        model = ClientReview
        fields = ['description', 'photo']
        widgets = {
            'description': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Введите текст отзыва клиента...',
                }
            ),
            'photo': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control',
                    'accept': 'image/*',
                }
            ),
        }
        labels = {
            'description': 'Описание отзыва',
            'photo': 'Фотография',
        }
