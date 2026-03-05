from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from django.urls import reverse_lazy
from . import views

urlpatterns = [
    path('grappelli/', include('grappelli.urls')),
    path('admin/', admin.site.urls),
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico', permanent=True)),
    path('', views.home, name='home'),
    path('support/', views.support, name='support'),
    path('accounts/', include('accounts.urls')),
    path('performers/', include('performers.urls')),
    path('interactions/', include(('interactions.urls', 'interactions'), namespace='interactions')),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path(
        'password-reset/',
        views.SafePasswordResetView.as_view(
            template_name='accounts/password_reset_form.html',
            email_template_name='accounts/emails/password_reset_email.txt',
            html_email_template_name='accounts/emails/password_reset_email.html',
            subject_template_name='accounts/emails/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done'),
        ),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='accounts/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='accounts/password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='accounts/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
    path('chat/', include('chat.urls')),
    path('announcements/', include('announcements.urls')),
    path('notifications/', include(('notifications.urls', 'notifications'), namespace='notifications')),
]

# Обслуживание медиа файлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
