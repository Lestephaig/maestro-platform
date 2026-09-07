from django.urls import path

from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('settings/', views.notification_settings, name='settings'),
    path(
        'channel-settings/',
        views.notification_channel_settings_update,
        name='channel_settings_update',
    ),
    path('api/settings/', views.notification_settings_api, name='settings_api'),
    path('mark-read/<int:notification_id>/', views.notification_mark_read, name='mark_read'),
    path('mark-all-read/', views.notification_mark_all_read, name='mark_all_read'),
]
