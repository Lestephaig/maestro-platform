from django import forms
from .models import AgentProfile


class AgentProfileForm(forms.ModelForm):
    class Meta:
        model = AgentProfile
        fields = [
            'display_name',
            'agency_name',
            'bio',
            'specialization',
            'experience_years',
            'website',
        ]
        widgets = {
            'display_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Имя или псевдоним организатора',
            }),
            'agency_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название агентства (если есть)',
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Расскажите о своем опыте, ключевых проектах и ценностях',
            }),
            'specialization': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Специализация (жанры, типы проектов)',
            }),
            'experience_years': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://example.com',
            }),
        }

