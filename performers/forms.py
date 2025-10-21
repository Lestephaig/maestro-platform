# performers/forms.py
from django import forms
from .models import PerformerProfile

class PerformerProfileForm(forms.ModelForm):
    class Meta:
        model = PerformerProfile
        fields = ['full_name', 'birth_year', 'education', 'achievements', 'voice_type', 'repertoire', 'bio', 'video_url', 'photo']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите ваше полное имя'
            }),
            'birth_year': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Год рождения'
            }),
            'education': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Образование, консерватория, университет...'
            }),
            'achievements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Награды, премии, достижения...'
            }),
            'voice_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: тенор, сопрано, баритон'
            }),
            'repertoire': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Опишите ваш репертуар, произведения, жанры...'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Расскажите о себе, своем опыте, достижениях и образовании...'
            }),
            'video_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.youtube.com/watch?v=...'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }