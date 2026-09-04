import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .models import Notification, NotificationPreference
from .preferences import (
    NotificationPreferenceValidationError,
    get_channel_settings,
    update_channel_settings,
)


@login_required
def notification_list(request):
    view_mode = request.GET.get('view', 'all')
    type_filter = request.GET.get('type', '')
    valid_types = {key for key, _ in Notification.NOTIFICATION_TYPE_CHOICES}
    preferences = {
        pref.notification_type: pref.in_app_enabled
        for pref in NotificationPreference.objects.filter(user=request.user)
    }
    enabled_in_app_types = [
        notification_type
        for notification_type, _ in Notification.NOTIFICATION_TYPE_CHOICES
        if preferences.get(notification_type, True)
    ]

    notifications_qs = request.user.notifications.filter(
        notification_type__in=enabled_in_app_types
    ).order_by('-sent_at')
    if view_mode == 'unread':
        notifications_qs = notifications_qs.filter(is_read=False)
    if type_filter in valid_types:
        notifications_qs = notifications_qs.filter(notification_type=type_filter)
    else:
        type_filter = ''

    paginator = Paginator(notifications_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'view_mode': view_mode if view_mode in {'all', 'unread'} else 'all',
        'type_filter': type_filter,
        'notification_type_choices': Notification.NOTIFICATION_TYPE_CHOICES,
        'unread_count': request.user.notifications.filter(
            is_read=False,
            notification_type__in=enabled_in_app_types,
        ).count(),
    }
    context.update(get_channel_settings(request.user))
    return render(request, 'notifications/notification_list.html', context)


@require_POST
@login_required
def notification_mark_read(request, notification_id):
    notification = get_object_or_404(Notification, pk=notification_id, user=request.user)
    notification.mark_read()
    return redirect(request.POST.get('next') or 'notifications:list')


@require_POST
@login_required
def notification_mark_all_read(request):
    request.user.notifications.filter(is_read=False).update(
        is_read=True,
        read_at=timezone.now(),
    )
    messages.success(request, 'Все уведомления отмечены как прочитанные.')
    return redirect(request.POST.get('next') or 'notifications:list')


@login_required
def notification_settings(request):
    return redirect('notifications:list')


@require_POST
@login_required
def notification_channel_settings_update(request):
    current_settings = get_channel_settings(request.user)
    update_channel_settings(request.user, {
        'email_enabled': bool(request.POST.get('email_enabled')),
        'telegram_enabled': (
            bool(request.POST.get('telegram_enabled'))
            if current_settings['telegram_linked']
            else False
        ),
    })
    messages.success(request, 'Настройки каналов уведомлений сохранены.')
    return redirect('notifications:list')


@login_required
@require_http_methods(['GET', 'PATCH', 'PUT'])
def notification_settings_api(request):
    if request.method == 'GET':
        return JsonResponse(get_channel_settings(request.user))

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({
            'error': 'invalid_json',
            'message': 'Тело запроса должно содержать корректный JSON.',
        }, status=400)

    try:
        channel_settings = update_channel_settings(request.user, payload)
    except NotificationPreferenceValidationError as error:
        return JsonResponse({
            'error': 'validation_error',
            'fields': error.errors,
        }, status=400)

    return JsonResponse(channel_settings)
