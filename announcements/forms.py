from django import forms
from .models import Announcement, AnnouncementResponse, Tag


class AnnouncementForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all().order_by('name'),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '10'}),
        label='Теги',
    )

    class Meta:
        model = Announcement
        fields = [
            'title',
            'announcement_type',
            'description',
            'tags',
            'city',
            'location',
            'is_online',
            'is_one_day',
            'start_date',
            'end_date',
            'application_deadline',
            'is_paid',
            'budget_amount',
            'budget_currency',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'announcement_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Город'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Локация'
            }),
            'is_online': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_one_day': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_is_one_day'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'id': 'id_start_date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'id': 'id_end_date'
            }),
            'application_deadline': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'is_paid': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'budget_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'budget_currency': forms.Select(attrs={
                'class': 'form-select'
            }),
        }



class AnnouncementResponseForm(forms.ModelForm):
    class Meta:
        model = AnnouncementResponse
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            })
        }
        labels = {
            'message': 'Сообщение'
        }

