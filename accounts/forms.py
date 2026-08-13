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

    accept_terms = forms.BooleanField(
        required=True,
        label="Я принимаю Пользовательское соглашение и Правила использования материалов на сайте.",
        error_messages={'required': 'Необходимо принять пользовательское соглашение и правила использования материалов.'},
    )

    accept_personal_data = forms.BooleanField(
        required=True,
        label="Я ознакомился(-ась) с Политикой обработки персональных данных и даю согласие на обработку персональных данных.",
        error_messages={'required': 'Необходимо дать согласие на обработку персональных данных.'},
    )
    
    first_name = forms.CharField(
        max_length=200,
        required=False,
        label="Имя",
    )

    last_name = forms.CharField(
        max_length=150,
        required=False,
        label="Фамилия",
    )

    country = forms.CharField(max_length=120, required=False, label='Страна')
    city = forms.CharField(max_length=120, required=False, label='Город')
    bio = forms.CharField(
        required=False,
        label='О себе',
        widget=forms.Textarea(attrs={'rows': 4}),
    )
    company_name = forms.CharField(max_length=200, required=False, label='Название площадки')
    address = forms.CharField(max_length=255, required=False, label='Адрес')
    contact_person = forms.CharField(max_length=200, required=False, label='Контактное лицо')

    ROLE_REQUIRED_FIELDS = {
        'performer': ('first_name', 'last_name', 'country', 'city', 'bio'),
        'agent': ('first_name', 'last_name', 'country', 'city', 'bio'),
        'client': ('company_name', 'country', 'city', 'address', 'contact_person'),
    }

    FIELD_REQUIRED_MESSAGES = {
        'first_name': 'Укажите имя.',
        'last_name': 'Укажите фамилию.',
        'country': 'Укажите страну.',
        'city': 'Укажите город.',
        'bio': 'Заполните информацию о себе.',
        'company_name': 'Укажите название площадки.',
        'address': 'Укажите адрес площадки.',
        'contact_person': 'Укажите контактное лицо.',
    }

    class Meta:
        model = User
        fields = (
            'role', 'first_name', 'last_name', 'company_name', 'country', 'city',
            'address', 'contact_person', 'bio', 'email', 'password1', 'password2',
            'accept_terms', 'accept_personal_data',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Убираем поле username из формы
        if 'username' in self.fields:
            del self.fields['username']
        self.fields['password1'].label = 'Пароль'
        self.fields['password2'].label = 'Подтверждение пароля'
        for field_name, field in self.fields.items():
            if field_name == 'role':
                continue
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'

        placeholders = {
            'first_name': 'Введите имя',
            'last_name': 'Введите фамилию',
            'company_name': 'Название площадки',
            'country': 'Например, Россия',
            'city': 'Например, Москва',
            'address': 'Улица, дом',
            'contact_person': 'ФИО и должность',
            'bio': 'Расскажите о себе и своём опыте',
            'email': 'name@example.com',
        }
        for field_name, placeholder in placeholders.items():
            self.fields[field_name].widget.attrs['placeholder'] = placeholder

    def clean(self):
        cleaned_data = super().clean()
        # Устанавливаем username = email для валидации
        if 'email' in cleaned_data:
            cleaned_data['username'] = cleaned_data['email']
        role = cleaned_data.get('role')
        for field_name in self.ROLE_REQUIRED_FIELDS.get(role, ()):
            value = cleaned_data.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                self.add_error(field_name, self.FIELD_REQUIRED_MESSAGES[field_name])
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        # Устанавливаем username равным email для совместимости с Django
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '').strip()
        user.last_name = self.cleaned_data.get('last_name', '').strip()
        user.display_name = f'{user.first_name} {user.last_name}'.strip()
        if self.cleaned_data.get('role') == 'client':
            user.display_name = self.cleaned_data.get('company_name', '').strip()
        user.role = self.cleaned_data.get('role', 'performer')
        if commit:
            user.save()
        return user
