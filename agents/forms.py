from django import forms
from accounts.form_mixins import UserNameProfileFormMixin
from .models import AgentProfile


class AgentProfileForm(UserNameProfileFormMixin, forms.ModelForm):
    class Meta:
        model = AgentProfile
        fields = [
            'first_name',
            'last_name',
            'agency_name',
            'bio',
            'country',
            'city',
            'specialization',
            'experience_years',
            'website',
        ]
        widgets = {
            'agency_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название агентства (если есть)',
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Расскажите о своем опыте, ключевых проектах и ценностях',
            }),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Страна'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Город'}),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ('bio', 'country', 'city'):
            self.fields[field_name].required = True

    def sync_display_name(self, profile, user):
        profile.display_name = f'{user.first_name} {user.last_name}'.strip()
