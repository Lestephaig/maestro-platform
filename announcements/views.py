from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import date

from .models import Announcement, AnnouncementResponse, Tag
from .forms import AnnouncementForm, AnnouncementResponseForm


def announcement_list(request):
    """Список объявлений с фильтрами"""
    announcements = Announcement.objects.filter(
        status__in=[Announcement.STATUS_PUBLISHED, Announcement.STATUS_COMPLETED],
        is_approved=True
    ).select_related('author').prefetch_related('tags').annotate(
        responses_count=Count('responses')
    )

    # Фильтры
    search_query = request.GET.get('q', '').strip()
    announcement_type = request.GET.get('type', '').strip()
    tag_slug = request.GET.get('tag', '').strip()
    location_query = request.GET.get('location', '').strip()
    is_online = request.GET.get('is_online')
    is_paid = request.GET.get('is_paid')
    budget_from = request.GET.get('budget_from', '').strip()
    budget_to = request.GET.get('budget_to', '').strip()
    currency = request.GET.get('currency', '').strip()
    deadline_soon = request.GET.get('deadline_soon')
    available_only = request.GET.get('available_only')

    # Поиск
    if search_query:
        announcements = announcements.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(city__icontains=search_query) |
            Q(location__icontains=search_query)
        )

    # Фильтр по типу
    if announcement_type in dict(Announcement.TYPE_CHOICES):
        announcements = announcements.filter(announcement_type=announcement_type)

    # Фильтр по тегу
    if tag_slug:
        announcements = announcements.filter(tags__slug=tag_slug)

    # Фильтр по локации (ищет в городе и локации)
    if location_query:
        announcements = announcements.filter(
            Q(city__icontains=location_query) |
            Q(location__icontains=location_query)
        )

    # Фильтр онлайн/офлайн
    if is_online == 'true':
        announcements = announcements.filter(is_online=True)
    elif is_online == 'false':
        announcements = announcements.filter(is_online=False)

    # Фильтр оплачиваемо/неоплачиваемо
    if is_paid == 'true':
        announcements = announcements.filter(is_paid=True)
    elif is_paid == 'false':
        announcements = announcements.filter(is_paid=False)

    # Фильтр по бюджету
    if budget_from:
        try:
            budget_from_float = float(budget_from)
            announcements = announcements.filter(budget_amount__gte=budget_from_float)
        except ValueError:
            pass

    if budget_to:
        try:
            budget_to_float = float(budget_to)
            announcements = announcements.filter(budget_amount__lte=budget_to_float)
        except ValueError:
            pass

    if currency in dict(Announcement.CURRENCY_CHOICES):
        announcements = announcements.filter(budget_currency=currency)

    # Фильтр "скоро дедлайн"
    if deadline_soon == 'true':
        from datetime import timedelta
        today = timezone.now().date()
        three_days_later = today + timedelta(days=3)
        announcements = announcements.filter(
            application_deadline__gte=today,
            application_deadline__lte=three_days_later
        )
    
    # Фильтр "Доступно" - только незавершенные с неистекшей датой отклика
    if available_only == 'true':
        today = timezone.now().date()
        announcements = announcements.filter(
            status=Announcement.STATUS_PUBLISHED
        ).filter(
            Q(application_deadline__gte=today) | Q(application_deadline__isnull=True)
        )

    # Сортировка
    sort = request.GET.get('sort', 'newest')
    if sort == 'newest':
        announcements = announcements.order_by('-published_at', '-created_at')
    elif sort == 'oldest':
        announcements = announcements.order_by('published_at', 'created_at')
    elif sort == 'deadline':
        announcements = announcements.order_by('application_deadline')
    elif sort == 'responses':
        announcements = announcements.order_by('-responses_count')

    # Пагинация
    paginator = Paginator(announcements, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Получаем все теги для фильтра
    all_tags = Tag.objects.annotate(
        announcement_count=Count('announcements', filter=Q(announcements__status=Announcement.STATUS_PUBLISHED))
    ).order_by('-announcement_count', 'name')

    context = {
        'page_obj': page_obj,
        'announcements': page_obj,
        'all_tags': all_tags,
        'announcement_types': Announcement.TYPE_CHOICES,
        'currencies': Announcement.CURRENCY_CHOICES,
        # Сохраняем параметры фильтров для формы
        'search_query': search_query,
        'announcement_type': announcement_type,
        'tag_slug': tag_slug,
        'location_query': location_query,
        'is_online': is_online,
        'is_paid': is_paid,
        'budget_from': budget_from,
        'budget_to': budget_to,
        'currency': currency,
        'deadline_soon': deadline_soon,
        'available_only': available_only,
        'sort': sort,
    }
    return render(request, 'announcements/announcement_list.html', context)


def announcement_detail(request, announcement_id):
    """Детальная страница объявления"""
    announcement = get_object_or_404(
        Announcement.objects.select_related('author').prefetch_related('tags'),
        id=announcement_id
    )

    # Проверяем, может ли пользователь видеть объявление
    if announcement.status not in [Announcement.STATUS_PUBLISHED, Announcement.STATUS_COMPLETED] and announcement.author != request.user:
        messages.error(request, 'Это объявление недоступно для просмотра.')
        return redirect('announcements:list')

    # Проверяем, откликнулся ли уже пользователь
    user_response = None
    if request.user.is_authenticated:
        try:
            user_response = AnnouncementResponse.objects.get(
                announcement=announcement,
                responder=request.user
            )
        except AnnouncementResponse.DoesNotExist:
            pass

    # Форма отклика
    response_form = None
    can_respond = (
        request.user.is_authenticated and
        request.user != announcement.author and
        announcement.status == Announcement.STATUS_PUBLISHED and
        announcement.is_approved and
        not user_response and
        (not announcement.application_deadline or announcement.application_deadline >= date.today())
    )

    if can_respond:
        if request.method == 'POST':
            response_form = AnnouncementResponseForm(request.POST)
            if response_form.is_valid():
                response = response_form.save(commit=False)
                response.announcement = announcement
                response.responder = request.user
                response.save()
                messages.success(request, 'Ваш отклик успешно отправлен!')
                return redirect('announcements:detail', announcement_id=announcement.id)
        else:
            response_form = AnnouncementResponseForm()

    context = {
        'announcement': announcement,
        'user_response': user_response,
        'response_form': response_form,
        'can_respond': can_respond,
    }
    return render(request, 'announcements/announcement_detail.html', context)


@login_required
def announcement_create(request):
    """Создание нового объявления"""
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.author = request.user
            announcement.status = Announcement.STATUS_PUBLISHED
            announcement.is_approved = True
            announcement.save()
            form.save_m2m()  # Сохраняем теги
            messages.success(request, 'Объявление успешно создано!')
            return redirect('announcements:detail', announcement_id=announcement.id)
    else:
        form = AnnouncementForm()

    context = {
        'form': form,
        'title': 'Создать объявление',
    }
    return render(request, 'announcements/announcement_form.html', context)


@login_required
def announcement_edit(request, announcement_id):
    """Редактирование объявления"""
    announcement = get_object_or_404(Announcement, id=announcement_id)

    # Проверяем права доступа
    if announcement.author != request.user and not request.user.is_staff:
        messages.error(request, 'У вас нет прав для редактирования этого объявления.')
        return redirect('announcements:detail', announcement_id=announcement.id)

    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, 'Объявление успешно обновлено!')
            return redirect('announcements:detail', announcement_id=announcement.id)
    else:
        form = AnnouncementForm(instance=announcement)

    context = {
        'form': form,
        'announcement': announcement,
        'title': 'Редактировать объявление',
    }
    return render(request, 'announcements/announcement_form.html', context)


@login_required
def my_announcements(request):
    """Мои объявления"""
    announcements = Announcement.objects.filter(
        author=request.user
    ).select_related('author').prefetch_related('tags').annotate(
        responses_count=Count('responses')
    ).order_by('-created_at')

    # Пагинация
    paginator = Paginator(announcements, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'announcements': page_obj,
    }
    return render(request, 'announcements/my_announcements.html', context)


@login_required
def announcement_complete(request, announcement_id):
    """Завершить объявление досрочно"""
    announcement = get_object_or_404(Announcement, id=announcement_id)
    
    # Проверяем права доступа
    if announcement.author != request.user and not request.user.is_staff:
        messages.error(request, 'У вас нет прав для завершения этого объявления.')
        return redirect('announcements:detail', announcement_id=announcement.id)
    
    # Проверяем, что объявление еще не завершено
    if announcement.status == Announcement.STATUS_COMPLETED:
        messages.warning(request, 'Объявление уже завершено.')
        return redirect('announcements:detail', announcement_id=announcement.id)
    
    if request.method == 'POST':
        announcement.status = Announcement.STATUS_COMPLETED
        announcement.save()
        messages.success(request, 'Объявление успешно завершено.')
        # Редирект на страницу "Мои объявления", чтобы увидеть обновленный статус
        return redirect('announcements:my_announcements')
    
    return redirect('announcements:detail', announcement_id=announcement.id)


@login_required
def announcement_responses(request, announcement_id):
    """Отклики на объявление (для автора)"""
    announcement = get_object_or_404(Announcement, id=announcement_id)

    # Проверяем права доступа
    if announcement.author != request.user and not request.user.is_staff:
        messages.error(request, 'У вас нет прав для просмотра откликов на это объявление.')
        return redirect('announcements:detail', announcement_id=announcement.id)

    responses = AnnouncementResponse.objects.filter(
        announcement=announcement
    ).select_related('responder').order_by('-created_at')

    # Обработка изменения статуса отклика
    if request.method == 'POST' and request.user == announcement.author:
        response_id = request.POST.get('response_id')
        new_status = request.POST.get('status')
        if response_id and new_status in dict(AnnouncementResponse.STATUS_CHOICES):
            try:
                response = AnnouncementResponse.objects.get(
                    id=response_id,
                    announcement=announcement
                )
                response.status = new_status
                response.save()
                messages.success(request, 'Статус отклика обновлен.')
                return redirect('announcements:responses', announcement_id=announcement.id)
            except AnnouncementResponse.DoesNotExist:
                messages.error(request, 'Отклик не найден.')

    context = {
        'announcement': announcement,
        'responses': responses,
    }
    return render(request, 'announcements/announcement_responses.html', context)
