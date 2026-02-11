# clients/forms.py
from django import forms
from .models import ClientProfile

class ClientProfileForm(forms.ModelForm):
    class Meta:
        model = ClientProfile
        fields = [
            'company_name',
            'address',
            'venue_type',
            'hall_capacity',
            'has_stage',
            'contact_person',
            'website',
            'stage_size',
            'microphones_count',
            'sound_system',
            'mixing_console',
            'lighting_equipment',
            'video_equipment',
            'has_internet',
            'power_supply',
            'has_green_rooms',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название площадки или организации'
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Город, улица, дом'
            }),
            'venue_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Концертный зал, театр, клуб...'
            }),
            'hall_capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Например: 500'
            }),
            'has_stage': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ваше имя и должность'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com'
            }),
            'stage_size': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: 10×8×6 м'
            }),
            'microphones_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Например: 8'
            }),
            'sound_system': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Модель/описание'
            }),
            'mixing_console': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Модель/описание'
            }),
            'lighting_equipment': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Модель/описание'
            }),
            'video_equipment': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Проекторы, экраны и т.д.'
            }),
            'has_internet': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'power_supply': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: 220В, 380В'
            }),
            'has_green_rooms': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }