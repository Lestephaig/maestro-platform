# performers/forms.py
from django import forms
from .models import PerformerProfile, PerformerPhoto, PerformerVideo, RepertoireItem

class PerformerProfileForm(forms.ModelForm):
    PERFORMER_TYPE_CHOICES = PerformerProfile.PERFORMER_TYPE_CHOICES
    VOICE_TYPE_CHOICES = [(value, value) for value in PerformerProfile.DEFAULT_VOICE_TYPES]
    INSTRUMENT_CHOICES = [(value, value) for value in PerformerProfile.DEFAULT_INSTRUMENTS]

    performer_type = forms.ChoiceField(
        choices=PERFORMER_TYPE_CHOICES,
        label='Тип исполнителя',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    voice_type = forms.ChoiceField(
        choices=[('', 'Выберите тип голоса')] + VOICE_TYPE_CHOICES,
        required=False,
        label='Тип голоса',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    instrument = forms.ChoiceField(
        choices=[('', 'Выберите инструмент')] + INSTRUMENT_CHOICES,
        required=False,
        label='Инструмент',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = PerformerProfile
        fields = [
            'full_name',
            'performer_type',
            'voice_type',
            'instrument',
            'birth_date',
            'education',
            'achievements',
            'bio',
            'video_url',
            'photo',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите ваше полное имя'
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'placeholder': 'дд.мм.гггг',
                'type': 'date'
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
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Расскажите о себе, своем опыте, достижениях и образовании...'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['birth_date'].label = 'Дата рождения'

        if self.instance and self.instance.voice_type:
            current_voice = (self.instance.voice_type, self.instance.voice_type)
            if current_voice not in self.fields['voice_type'].choices:
                self.fields['voice_type'].choices.append(current_voice)

        if self.instance and self.instance.instrument:
            current_instrument = (self.instance.instrument, self.instance.instrument)
            if current_instrument not in self.fields['instrument'].choices:
                self.fields['instrument'].choices.append(current_instrument)

    def clean(self):
        cleaned = super().clean()
        performer_type = cleaned.get('performer_type')
        voice_type = cleaned.get('voice_type')
        instrument = cleaned.get('instrument')

        if performer_type == PerformerProfile.PERFORMER_TYPE_VOCALIST:
            if not voice_type:
                self.add_error('voice_type', 'Выберите тип голоса.')
            cleaned['instrument'] = ''
        elif performer_type == PerformerProfile.PERFORMER_TYPE_INSTRUMENTALIST:
            if not instrument:
                self.add_error('instrument', 'Выберите основной инструмент.')
            cleaned['voice_type'] = ''

        return cleaned


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