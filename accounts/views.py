from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from .forms import CustomUserCreationForm
from performers.models import PerformerProfile
from clients.models import ClientProfile
from django.contrib.auth.decorators import login_required
from performers.forms import PerformerProfileForm
from clients.forms import ClientProfileForm

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Создаём профиль в зависимости от роли
            role = form.cleaned_data.get('role')
            if role == 'performer':
                PerformerProfile.objects.create(user=user, full_name=user.username)
            elif role == 'client':
                ClientProfile.objects.create(user=user, company_name=user.username)

            # Автоматический вход после регистрации
            login(request, user)
            return redirect('profile')  # пока заглушка
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})
@login_required
def profile(request):
    return render(request, 'accounts/profile.html')

@login_required
def profile_view(request):
    """Возвращает только содержимое профиля для HTMX"""
    return render(request, 'accounts/_profile_content.html')
@login_required
def profile_edit(request):
    if hasattr(request.user, 'performer_profile'):
        profile = request.user.performer_profile
        form_class = PerformerProfileForm
    elif hasattr(request.user, 'client_profile'):
        profile = request.user.client_profile
        form_class = ClientProfileForm
    else:
        return redirect('profile')

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            # Возвращаем только содержимое профиля для HTMX
            return render(request, 'accounts/_profile_content.html')
    else:
        form = form_class(instance=profile)

    # Возвращаем только частичный шаблон редактирования
    return render(request, 'accounts/_profile_edit.html', {'form': form})