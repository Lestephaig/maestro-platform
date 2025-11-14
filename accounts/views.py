from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.http import JsonResponse
from django.contrib import messages
from .forms import CustomUserCreationForm
from .utils import send_verification_email, verify_email_token
from performers.models import PerformerProfile, PerformerPhoto, PerformerVideo
from clients.models import ClientProfile
from agents.models import AgentProfile
from django.contrib.auth.decorators import login_required
from performers.forms import PerformerProfileForm, PerformerPhotoForm, PerformerVideoForm
from clients.forms import ClientProfileForm
from agents.forms import AgentProfileForm
from interactions.models import Interaction, InteractionParticipant
from django.db.models import Q


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
            elif role == 'agent':
                AgentProfile.objects.create(user=user, display_name=user.username)

            # Отправляем email для подтверждения
            try:
                send_verification_email(user, request)
                messages.success(
                    request,
                    'Регистрация успешна! Пожалуйста, проверьте вашу почту и подтвердите email адрес.'
                )
                return redirect('email_verification_sent')
            except Exception as e:
                # Если не удалось отправить email, все равно показываем сообщение
                messages.warning(
                    request,
                    'Регистрация успешна, но не удалось отправить email подтверждения. '
                    'Пожалуйста, свяжитесь с администратором.'
                )
                # Автоматический вход, если email не отправился
                login(request, user)
                return redirect('profile')
    else:
        form = CustomUserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})


def email_verification_sent(request):
    """Страница с информацией об отправке email подтверждения"""
    return render(request, 'accounts/email_verification_sent.html')


def verify_email(request, uidb64, token):
    """Подтверждение email адреса"""
    user = verify_email_token(uidb64, token)
    
    if user:
        messages.success(request, 'Ваш email адрес успешно подтвержден!')
        # Автоматически входим пользователя после подтверждения
        login(request, user)
        return redirect('profile')
    else:
        messages.error(request, 'Неверная или устаревшая ссылка подтверждения.')
        return redirect('register')


def _build_profile_context(user):
    context = {}
    base_queryset = Interaction.objects.select_related('created_by').prefetch_related('participant_links__user')

    if hasattr(user, 'agent_profile'):
        agent_interactions = base_queryset.filter(
            Q(created_by=user) | Q(participant_links__user=user, participant_links__role=InteractionParticipant.ROLE_AGENT)
        ).distinct().order_by('-created_at')
        context['agent_interactions'] = agent_interactions
        context['agent_active_interactions'] = agent_interactions.filter(status__in=[
            Interaction.STATUS_IN_PROGRESS,
            Interaction.STATUS_PROPOSAL_SENT,
        ])

    if hasattr(user, 'client_profile'):
        client_interactions = base_queryset.filter(
            Q(created_by=user) | Q(participant_links__user=user, participant_links__role=InteractionParticipant.ROLE_VENUE)
        ).distinct().order_by('-created_at')
        context['client_interactions'] = client_interactions

    if hasattr(user, 'performer_profile'):
        performer_interactions = base_queryset.filter(
            Q(created_by=user) | Q(participant_links__user=user, participant_links__role=InteractionParticipant.ROLE_PERFORMER)
        ).distinct().order_by('-created_at')
        context['performer_interactions'] = performer_interactions
    return context


@login_required
def profile(request):
    context = _build_profile_context(request.user)
    return render(request, 'accounts/profile.html', context)
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
    context = _build_profile_context(request.user)
    return render(request, 'accounts/_profile_content.html', context)
@login_required
def profile_edit(request):
    if hasattr(request.user, 'performer_profile'):
        profile = request.user.performer_profile
        form_class = PerformerProfileForm
    elif hasattr(request.user, 'client_profile'):
        profile = request.user.client_profile
        form_class = ClientProfileForm
    elif hasattr(request.user, 'agent_profile'):
        profile = request.user.agent_profile
        form_class = AgentProfileForm
    else:
        return redirect('profile')

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            # Возвращаем только содержимое профиля для HTMX
            context = _build_profile_context(request.user)
            return render(request, 'accounts/_profile_content.html', context)
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