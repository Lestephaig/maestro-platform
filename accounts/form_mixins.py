from django import forms


class UserNameProfileFormMixin(forms.Form):
    """Expose the account name fields together with a role profile form."""

    first_name = forms.CharField(
        label='Имя',
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя'}),
    )
    last_name = forms.CharField(
        label='Фамилия',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Фамилия'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name'].strip()
        user.last_name = self.cleaned_data['last_name'].strip()
        self.sync_display_name(profile, user)
        if commit:
            user.save(update_fields=['first_name', 'last_name'])
            profile.save()
            self.save_m2m()
        return profile

    def sync_display_name(self, profile, user):
        """Role forms may synchronize their legacy combined-name field."""
