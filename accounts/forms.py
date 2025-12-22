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

    email = forms.EmailField(
        required=True,
        label="Email"
    )
    
    display_name = forms.CharField(
        max_length=150,
        required=True,
        label="Имя пользователя"
    )

    class Meta:
        model = User
        fields = ("email", "display_name", "password1", "password2", "role")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Убираем поле username из формы
        if 'username' in self.fields:
            del self.fields['username']

    def clean(self):
        cleaned_data = super().clean()
        # Устанавливаем username = email для валидации
        if 'email' in cleaned_data:
            cleaned_data['username'] = cleaned_data['email']
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        # Устанавливаем username равным email для совместимости с Django
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.display_name = self.cleaned_data.get('display_name', '')
        user.role = self.cleaned_data.get('role', 'performer')
        if commit:
            user.save()
        return user