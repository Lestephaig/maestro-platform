# performers/forms.py
from django import forms
from .models import PerformerProfile

class PerformerProfileForm(forms.ModelForm):
    class Meta:
        model = PerformerProfile
        fields = ['full_name', 'voice_type', 'repertoire', 'bio', 'video_url', 'photo_url']
        widgets = {
            'repertoire': forms.Textarea(attrs={'rows': 4}),
            'bio': forms.Textarea(attrs={'rows': 4}),
        }