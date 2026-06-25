from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.http import JsonResponse
from django.contrib import messages
import logging
from .forms import CustomUserCreationForm
from .utils import send_verification_email, verify_email_token
from performers.models import PerformerProfile, PerformerPhoto, PerformerVideo
from clients.models import ClientProfile
from agents.models import AgentProfile
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db import transaction
from performers.forms import PerformerProfileForm, PerformerPhotoForm, PerformerVideoForm
from clients.forms import ClientProfileForm
from agents.forms import AgentProfileForm
from interactions.models import Interaction, InteractionParticipant
from django.db.models import Q, Count
from django.core.paginator import Paginator
from chat.models import ChatRoom
from announcements.models import Announcement
from core.legal import get_client_ip, get_required_documents, get_user_agent
from .models import LegalAcceptance

logger = logging.getLogger(__name__)


def record_required_legal_acceptances(user, request):
    ip_address = get_client_ip(request) or None
    user_agent = get_user_agent(request)
    acceptances = []
    for slug, document in get_required_documents().items():
        acceptances.append(
            LegalAcceptance(
                user=user,
                document_slug=slug,
                document_title=document['title'],
                document_version=document['version'],
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )
    LegalAcceptance.objects.bulk_create(acceptances, ignore_conflicts=True)

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                # Создаём профиль в зависимости от роли
                role = form.cleaned_data.get('role')
                # Используем display_name, если оно есть, иначе email
                display_name = user.display_name or user.email
                if role == 'performer':
                    PerformerProfile.objects.create(user=user, full_name=display_name)
                elif role == 'client':
                    ClientProfile.objects.create(user=user, company_name=display_name)
                elif role == 'agent':
                    AgentProfile.objects.create(user=user, display_name=display_name)
                record_required_legal_acceptances(user, request)

            # Отправляем email для подтверждения
            try:
                send_verification_email(user, request)
                request.session['pending_verification_email'] = user.email
                messages.success(
                    request,
                    'Регистрация успешна! Пожалуйста, подтвердите email адрес.'
                )
                return redirect('email_verification_sent')
            except Exception:
                logger.exception('Failed to send verification email during registration')
                # Если не удалось отправить email, показываем предупреждение и разрешаем вход
                messages.warning(
                    request,
                    'Регистрация успешна, но не удалось отправить email подтверждения. '
                    'Пожалуйста, попробуйте позже или свяжитесь с администратором.'
                )
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


def resend_verification_email(request):
    if request.method != 'POST':
        return redirect('email_verification_sent')

    from .models import User
    email = request.session.get('pending_verification_email')
    user = None
    if email:
        user = User.objects.filter(email=email).first()
    elif request.user.is_authenticated:
        user = request.user
        request.session['pending_verification_email'] = user.email

    if not user:
        messages.error(request, 'Пользователь не найден.')
        return redirect('email_verification_sent')

    if user.is_email_verified:
        messages.info(request, 'Email уже подтверждён.')
        return redirect('login')

    try:
        send_verification_email(user, request)
        messages.success(request, 'Письмо подтверждения отправлено повторно.')
    except Exception:
        logger.exception('Failed to resend verification email')
        messages.error(request, 'Не удалось отправить письмо. Попробуйте позже.')

    return redirect('email_verification_sent')


def _build_profile_context(user, request=None):
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

    if getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False):
        from .models import User
        request_get = request.GET if request is not None else {}
        admin_users_q = (request_get.get('admin_users_q') or '').strip()
        admin_chats_q = (request_get.get('admin_chats_q') or '').strip()
        admin_announcements_q = (request_get.get('admin_announcements_q') or '').strip()
        admin_tab = request_get.get('admin_tab') or 'users'

        users_queryset = User.objects.order_by('-date_joined')
        if admin_users_q:
            users_queryset = users_queryset.filter(
                Q(display_name__icontains=admin_users_q)
                | Q(email__icontains=admin_users_q)
                | Q(username__icontains=admin_users_q)
            )

        users_paginator = Paginator(users_queryset, 50)
        users_page = users_paginator.get_page(request_get.get('admin_users_page') or 1)

        chats_queryset = (
            ChatRoom.objects.select_related(
                'performer',
                'client',
                'performer__performer_profile',
                'performer__agent_profile',
                'performer__client_profile',
                'client__performer_profile',
                'client__agent_profile',
                'client__client_profile',
            )
            .annotate(messages_count=Count('messages'))
            .order_by('-created_at')
        )
        if admin_chats_q:
            chats_queryset = chats_queryset.filter(
                Q(performer__display_name__icontains=admin_chats_q)
                | Q(performer__username__icontains=admin_chats_q)
                | Q(performer__email__icontains=admin_chats_q)
                | Q(performer__performer_profile__full_name__icontains=admin_chats_q)
                | Q(performer__agent_profile__display_name__icontains=admin_chats_q)
                | Q(performer__client_profile__company_name__icontains=admin_chats_q)
                | Q(client__display_name__icontains=admin_chats_q)
                | Q(client__username__icontains=admin_chats_q)
                | Q(client__email__icontains=admin_chats_q)
                | Q(client__performer_profile__full_name__icontains=admin_chats_q)
                | Q(client__agent_profile__display_name__icontains=admin_chats_q)
                | Q(client__client_profile__company_name__icontains=admin_chats_q)
            )
        chats_paginator = Paginator(chats_queryset, 50)
        chats_page = chats_paginator.get_page(request_get.get('admin_chats_page') or 1)

        announcements_queryset = (
            Announcement.objects.select_related('author')
            .order_by('-published_at', '-created_at')
        )
        if admin_announcements_q:
            announcements_queryset = announcements_queryset.filter(
                title__icontains=admin_announcements_q
            )
        announcements_paginator = Paginator(announcements_queryset, 50)
        announcements_page = announcements_paginator.get_page(
            request_get.get('admin_announcements_page') or 1
        )

        context['admin_tab'] = admin_tab if admin_tab in {'users', 'chats', 'announcements'} else 'users'
        context['admin_users_q'] = admin_users_q
        context['admin_chats_q'] = admin_chats_q
        context['admin_announcements_q'] = admin_announcements_q
        context['admin_users_total'] = User.objects.count()
        context['admin_users_filtered_total'] = users_queryset.count()
        context['admin_users_page_obj'] = users_page
        context['admin_users'] = users_page.object_list
        context['admin_chats_total'] = ChatRoom.objects.count()
        context['admin_chats_filtered_total'] = chats_queryset.count()
        context['admin_chats_page_obj'] = chats_page
        context['admin_chats'] = chats_page.object_list
        context['admin_announcements_total'] = Announcement.objects.count()
        context['admin_announcements_filtered_total'] = announcements_queryset.count()
        context['admin_announcements_page_obj'] = announcements_page
        context['admin_announcements'] = announcements_page.object_list
    return context


@login_required
def profile(request):
    context = _build_profile_context(request.user, request)
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


def venues_list(request):
    venues = ClientProfile.objects.select_related('user').order_by('-created_at')
    return render(request, 'accounts/venues_list.html', {'venues': venues})


def agents_list(request):
    agents = AgentProfile.objects.select_related('user').order_by('-created_at')
    return render(request, 'accounts/agents_list.html', {'agents': agents})


def agent_public_profile(request, user_id):
    """Публичный профиль организатора"""
    from .models import User

    agent_user = get_object_or_404(User, id=user_id)

    if not hasattr(agent_user, 'agent_profile'):
        if hasattr(agent_user, 'performer_profile'):
            return redirect('performers:performer_detail', performer_id=agent_user.performer_profile.id)
        if hasattr(agent_user, 'client_profile'):
            return redirect('client_public_profile', user_id=agent_user.id)

    context = {
        'agent_user': agent_user,
        'is_own_profile': request.user == agent_user,
    }

    return render(request, 'accounts/agent_public_profile.html', context)

@login_required
@require_POST
def admin_delete_user(request, user_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('profile')

    from .models import User
    target_user = get_object_or_404(User, id=user_id)

    if target_user == request.user:
        messages.error(request, 'Нельзя удалить собственный аккаунт.')
        return redirect('profile')

    if target_user.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Недостаточно прав для удаления администратора.')
        return redirect('profile')

    target_user.delete()
    messages.success(request, 'Пользователь удалён.')
    return redirect('profile')


@login_required
@require_POST
def admin_delete_announcement(request, announcement_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('profile')

    announcement = get_object_or_404(Announcement, id=announcement_id)
    announcement.delete()
    messages.success(request, 'Объявление удалено.')
    return redirect('profile')

@login_required
def profile_view(request):
    """Возвращает только содержимое профиля для HTMX"""
    context = _build_profile_context(request.user, request)
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
            context = _build_profile_context(request.user, request)
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
@require_POST
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
@require_POST
def delete_video(request, video_id):
    """Удалить видео"""
    video = get_object_or_404(PerformerVideo, id=video_id)
    
    if video.performer.user != request.user:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    video.delete()
    return JsonResponse({'success': True})
