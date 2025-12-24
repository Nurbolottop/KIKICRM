from django import forms

from apps.cms.models import Services, ServiceTaskTemplate


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Services
        fields = [
            "title",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
        }


class ServiceTaskTemplateForm(forms.ModelForm):
    class Meta:
        model = ServiceTaskTemplate
        fields = [
            "description",
        ]
        widgets = {
            "description": forms.TextInput(attrs={"class": "form-control"}),
        }
