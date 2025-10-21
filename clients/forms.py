# clients/forms.py
from django import forms
from .models import ClientProfile

class ClientProfileForm(forms.ModelForm):
    class Meta:
        model = ClientProfile
        fields = ['company_name', 'contact_person', 'website']
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название вашей компании или организации'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ваше имя и должность'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com'
            }),
        }