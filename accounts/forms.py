from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class CustomUserCreationForm(UserCreationForm):
    ROLE_CHOICES = [
        ('performer', 'Я исполнитель'),
        ('client', 'Я площадка'),
        ('agent', 'Я организатор'),
    ]

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect,
        label="Выберите тип аккаунта"
    )

    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2", "role")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.cleaned_data.get('role', 'performer')
        if commit:
            user.save()
        return user