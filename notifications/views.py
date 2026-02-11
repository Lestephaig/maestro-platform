from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Notification, NotificationPreference


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

    return render(request, 'notifications/notification_list.html', {
        'page_obj': page_obj,
        'view_mode': view_mode if view_mode in {'all', 'unread'} else 'all',
        'type_filter': type_filter,
        'notification_type_choices': Notification.NOTIFICATION_TYPE_CHOICES,
        'unread_count': request.user.notifications.filter(
            is_read=False,
            notification_type__in=enabled_in_app_types,
        ).count(),
    })


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
    if request.method == 'POST':
        for notification_type, _ in Notification.NOTIFICATION_TYPE_CHOICES:
            in_app_enabled = bool(request.POST.get(f'in_app_{notification_type}'))
            email_enabled = bool(request.POST.get(f'email_{notification_type}'))
            NotificationPreference.objects.update_or_create(
                user=request.user,
                notification_type=notification_type,
                defaults={
                    'in_app_enabled': in_app_enabled,
                    'email_enabled': email_enabled,
                },
            )
        messages.success(request, 'Настройки уведомлений сохранены.')
        return redirect('notifications:settings')

    preferences = {
        pref.notification_type: pref
        for pref in NotificationPreference.objects.filter(user=request.user)
    }
    rows = []
    for notification_type, label in Notification.NOTIFICATION_TYPE_CHOICES:
        preference = preferences.get(notification_type)
        rows.append({
            'notification_type': notification_type,
            'label': label,
            'in_app_enabled': True if preference is None else preference.in_app_enabled,
            'email_enabled': True if preference is None else preference.email_enabled,
        })

    return render(request, 'notifications/notification_settings.html', {
        'rows': rows,
    })
