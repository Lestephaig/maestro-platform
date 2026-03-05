import logging

from django.conf import settings
from django.contrib.auth import views as auth_views
from django.http import HttpResponseRedirect
from django.shortcuts import render

logger = logging.getLogger(__name__)

def home(request):
    """Главная страница платформы"""
    return render(request, 'home.html')


def support(request):
    """Страница поддержки и контактов"""
    return render(request, 'support.html')


class SafePasswordResetView(auth_views.PasswordResetView):
    """
    Avoid hard 500 on password reset submit when SMTP is temporarily unavailable.
    In DEBUG we keep the exception behavior for faster diagnostics.
    """

    def form_valid(self, form):
        opts = {
            'use_https': self.request.is_secure(),
            'token_generator': self.token_generator,
            'from_email': self.from_email,
            'email_template_name': self.email_template_name,
            'subject_template_name': self.subject_template_name,
            'request': self.request,
            'html_email_template_name': self.html_email_template_name,
            'extra_email_context': self.extra_email_context,
        }
        try:
            form.save(**opts)
        except Exception:
            logger.exception('Password reset email send failed')
            if settings.DEBUG:
                raise
        return HttpResponseRedirect(self.get_success_url())