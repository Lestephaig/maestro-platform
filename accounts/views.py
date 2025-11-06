from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.http import JsonResponse
from .forms import CustomUserCreationForm
from performers.models import PerformerProfile, PerformerPhoto, PerformerVideo
from clients.models import ClientProfile
from django.contrib.auth.decorators import login_required
from performers.forms import PerformerProfileForm, PerformerPhotoForm, PerformerVideoForm
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
def client_public_profile(request, user_id):
    """Публичный профиль заказчика"""
    from .models import User
    
    client_user = get_object_or_404(User, id=user_id)
    
    # Проверяем, что это действительно заказчик
    if not hasattr(client_user, 'client_profile'):
        # Если это артист, редиректим на его профиль артиста
        if hasattr(client_user, 'performer_profile'):
            from django.shortcuts import redirect
            return redirect('performers:performer_detail', performer_id=client_user.performer_profile.id)
        # Если вообще нет профиля, показываем базовую информацию
    
    context = {
        'client_user': client_user,
        'is_own_profile': request.user == client_user,
    }
    
    return render(request, 'accounts/client_public_profile.html', context)

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


@login_required
def manage_media(request):
    """Управление фото и видео артиста"""
    if not hasattr(request.user, 'performer_profile'):
        return redirect('profile')
    
    performer = request.user.performer_profile
    photos = performer.photos.all()
    videos = performer.videos.all()
    
    return render(request, 'accounts/_profile_media.html', {
        'photos': photos,
        'videos': videos,
        'photo_form': PerformerPhotoForm(),
        'video_form': PerformerVideoForm(),
    })


@login_required
def add_photo(request):
    """Добавить фото"""
    if not hasattr(request.user, 'performer_profile'):
        return JsonResponse({'error': 'Not a performer'}, status=403)
    
    if request.method == 'POST':
        form = PerformerPhotoForm(request.POST, request.FILES)
        if form.is_valid():
            photo = form.save(commit=False)
            photo.performer = request.user.performer_profile
            photo.save()
            # Перенаправляем на вкладку медиа
            return redirect('profile')
    
    return redirect('profile')


@login_required
def delete_photo(request, photo_id):
    """Удалить фото"""
    photo = get_object_or_404(PerformerPhoto, id=photo_id)
    
    if photo.performer.user != request.user:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    photo.delete()
    return JsonResponse({'success': True})


@login_required
def add_video(request):
    """Добавить видео"""
    if not hasattr(request.user, 'performer_profile'):
        return JsonResponse({'error': 'Not a performer'}, status=403)
    
    if request.method == 'POST':
        form = PerformerVideoForm(request.POST)
        if form.is_valid():
            video = form.save(commit=False)
            video.performer = request.user.performer_profile
            video.save()
            return redirect('profile')
    
    return redirect('profile')


@login_required
def delete_video(request, video_id):
    """Удалить видео"""
    video = get_object_or_404(PerformerVideo, id=video_id)
    
    if video.performer.user != request.user:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    video.delete()
    return JsonResponse({'success': True})