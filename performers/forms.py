# performers/forms.py
from django import forms
from .models import PerformerProfile, PerformerPhoto, PerformerVideo, RepertoireItem

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


class PerformerPhotoForm(forms.ModelForm):
    class Meta:
        model = PerformerPhoto
        fields = ['photo', 'caption', 'order']
        widgets = {
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'caption': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Подпись к фотографии (необязательно)'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Порядок (0 = первое)'
            }),
        }


class PerformerVideoForm(forms.ModelForm):
    class Meta:
        model = PerformerVideo
        fields = ['video_url', 'title', 'description', 'order']
        widgets = {
            'video_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.youtube.com/watch?v=...'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название видео'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Описание видео (необязательно)'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Порядок (0 = первое)'
            }),
        }


class RepertoireItemForm(forms.ModelForm):
    class Meta:
        model = RepertoireItem
        fields = ['composer', 'work_title', 'category', 'epoch', 'role_or_part', 'year_performed', 'notes', 'video_link', 'is_featured']
        widgets = {
            'composer': forms.TextInput(attrs={
                'class': 'form-control autocomplete-composer',
                'placeholder': 'Начните вводить имя композитора...',
                'autocomplete': 'off',
                'list': 'composers-list'
            }),
            'work_title': forms.TextInput(attrs={
                'class': 'form-control autocomplete-work',
                'placeholder': 'Начните вводить название произведения...',
                'autocomplete': 'off',
                'list': 'works-list'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'epoch': forms.Select(attrs={
                'class': 'form-select'
            }),
            'role_or_part': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Дон Жуан, 1-я часть, Soprano solo...'
            }),
            'year_performed': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Год исполнения (опционально)',
                'min': '1900',
                'max': '2100'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Дополнительные заметки (опционально)'
            }),
            'video_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.youtube.com/watch?v=... (опционально)'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'composer': 'Композитор',
            'work_title': 'Название произведения',
            'category': 'Категория',
            'epoch': 'Эпоха',
            'role_or_part': 'Роль / Партия',
            'year_performed': 'Год исполнения',
            'notes': 'Заметки',
            'video_link': 'Ссылка на видео',
            'is_featured': 'Отметить как избранное',
        }