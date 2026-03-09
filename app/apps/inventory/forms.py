from django import forms
from .models import Product, StockMovement, WriteOff, InventoryCheck, InventoryCheckItem


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "category", "unit", "description", "photo", "min_quantity", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "unit": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "min_quantity": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class StockMovementForm(forms.ModelForm):
    """Форма для прихода товара"""
    class Meta:
        model = StockMovement
        fields = ["product", "quantity", "reason", "notes"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "reason": forms.Select(attrs={"class": "form-select"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class OrderIssueForm(forms.Form):
    """Форма выдачи товара на заказ"""
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Товар"
    )
    quantity = forms.DecimalField(
        min_value=0.01,
        decimal_places=2,
        max_digits=10,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        label="Количество"
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        label="Примечания"
    )


class WriteOffForm(forms.ModelForm):
    class Meta:
        model = WriteOff
        fields = ["product", "quantity", "reason", "reason_other", "notes"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "reason": forms.Select(attrs={"class": "form-select"}),
            "reason_other": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }


class InventoryCheckForm(forms.ModelForm):
    """Создание инвентаризации"""
    class Meta:
        model = InventoryCheck
        fields = ["name", "notes"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class InventoryCheckItemForm(forms.ModelForm):
    """Форма для подсчёта товара при инвентаризации"""
    class Meta:
        model = InventoryCheckItem
        fields = ["actual_quantity", "notes"]
        widgets = {
            "actual_quantity": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "notes": forms.TextInput(attrs={"class": "form-control"}),
        }
