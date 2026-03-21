from django import forms
from django.utils import timezone
from .models import Order, OrderPhoto
from apps.clients.models import Client
from apps.services.models import Service


class OrderForm(forms.ModelForm):
    """Форма для создания и редактирования заказа."""
    
    class Meta:
        model = Order
        fields = [
            'client', 'category', 'service', 'status',
            'operator_status', 'manager_status', 'handed_to_manager',
            'address', 
            'property_type', 'scheduled_date', 'scheduled_time',
            'preliminary_price', 'rooms_count', 'area',
            'windows_count', 'bathrooms_count', 'after_renovation', 'work_scope',
            'lead_channel', 'priority', 'prepayment_amount',
            'price',
            'comment'
        ]
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'service': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'operator_status': forms.Select(attrs={'class': 'form-select'}),
            'manager_status': forms.Select(attrs={'class': 'form-select'}),
            'handed_to_manager': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Адрес выполнения уборки'}),
            'property_type': forms.Select(attrs={'class': 'form-select'}),
            'scheduled_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'scheduled_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'preliminary_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'rooms_count': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
            'area': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Площадь в м²'}),
            'windows_count': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'bathrooms_count': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
            'after_renovation': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'work_scope': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Пример: 50м², 2 комнаты, кухня, балкон'}),
            'lead_channel': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'prepayment_amount': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Итоговая цена'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Комментарий к заказу'}),
        }
        labels = {
            'client': 'Клиент',
            'category': 'Категория заказа',
            'service': 'Услуга',
            'status': 'Статус',
            'operator_status': 'Статус (оператор)',
            'manager_status': 'Статус (менеджер)',
            'handed_to_manager': 'Передано менеджеру',
            'address': 'Адрес выполнения',
            'property_type': 'Тип помещения',
            'scheduled_date': 'Дата уборки',
            'scheduled_time': 'Время уборки',
            'preliminary_price': 'Предварительная стоимость',
            'rooms_count': 'Количество комнат',
            'area': 'Площадь (м²)',
            'windows_count': 'Количество окон',
            'bathrooms_count': 'Количество санузлов',
            'after_renovation': 'После ремонта',
            'work_scope': 'Объём работы',
            'lead_channel': 'Канал привлечения',
            'priority': 'Приоритет',
            'prepayment_amount': 'Сумма предоплаты',
            'price': 'Итоговая стоимость',
            'comment': 'Заметки',
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Оптимизация queryset для выпадающих списков
        self.fields['client'].queryset = Client.objects.all().order_by('first_name', 'last_name')
        self.fields['service'].queryset = Service.objects.filter(is_active=True).order_by('name')
        
        # Установка начальной даты и времени (сегодня, текущее время)
        # Убираем initial values для числовых полей чтобы показывались placeholders
        if not self.instance.pk:
            self.fields['scheduled_date'].initial = timezone.now().date()
            self.fields['scheduled_time'].initial = timezone.now().time()
            # Устанавливаем пустые значения для числовых полей чтобы показывались placeholders
            self.fields['rooms_count'].initial = None
            self.fields['bathrooms_count'].initial = None
            self.fields['windows_count'].initial = None
            self.fields['preliminary_price'].initial = None
            self.fields['area'].initial = None
            # Устанавливаем начальные статусы
            self.fields['status'].initial = 'PROCESSING'
            self.fields['operator_status'].initial = 'IN_PROGRESS'
            self.fields['manager_status'].initial = 'WAITING'
        
        # Если клиент передан через initial, делаем поле скрытым (не disabled!)
        if self.initial.get('client'):
            self.fields['client'].widget = forms.HiddenInput()
        
        # Скрываем поля статусов от операторов (только менеджеры видят)
        if user and not self._is_manager(user):
            self.fields['operator_status'].widget = forms.HiddenInput()
            self.fields['manager_status'].widget = forms.HiddenInput()
            self.fields['handed_to_manager'].widget = forms.HiddenInput()

            # Итоговую цену задаёт менеджер — для оператора поле не должно быть обязательным
            # и не должно отображаться.
            if 'price' in self.fields:
                self.fields['price'].required = False
                self.fields['price'].widget = forms.HiddenInput()
                if self.initial.get('price') is None:
                    self.initial['price'] = 0

        # OPERATOR не должен редактировать поля менеджера
        if user and self._is_operator(user) and not user.is_superuser:
            manager_fields = ['price', 'manager_status', 'assigned_manager']
            for name in manager_fields:
                if name in self.fields:
                    self.fields[name].disabled = True

        # MANAGER не должен редактировать поля, которые заполняет OPERATOR
        if user and self._is_manager(user) and not user.is_superuser:
            operator_fields = [
                'client', 'category', 'service', 'status', 'operator_status',
                'address', 'property_type', 'scheduled_date', 'scheduled_time',
                'preliminary_price', 'rooms_count', 'area',
                'windows_count', 'bathrooms_count', 'after_renovation', 'work_scope',
                'lead_channel', 'priority', 'prepayment_amount',
            ]
            for name in operator_fields:
                if name in self.fields:
                    self.fields[name].disabled = True
    
    def _is_operator(self, user):
        """Проверка является ли пользователь оператором."""
        if hasattr(user, 'role'):
            return user.role in ['OPERATOR']
        return False

    def _is_manager(self, user):
        """Проверка является ли пользователь менеджером или админом."""
        if hasattr(user, 'role'):
            return user.role in ['MANAGER', 'ADMIN', 'SUPER_ADMIN']
        return user.is_staff or user.is_superuser


class OrderPhotoForm(forms.ModelForm):
    """Форма для загрузки фото заказа."""
    
    class Meta:
        model = OrderPhoto
        fields = ['photo', 'photo_type', 'comment']
        widgets = {
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'photo_type': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Комментарий к фото'}),
        }
