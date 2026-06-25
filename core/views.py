import logging

from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from accounts.models import CookieConsent
from accounts.views import record_required_legal_acceptances
from .legal import (
    LEGAL_DOCUMENTS,
    get_client_ip,
    get_cookie_policy,
    get_document,
    get_document_text,
    get_required_documents,
    get_user_agent,
    user_has_required_legal_acceptances,
)

logger = logging.getLogger(__name__)

def home(request):
    """Главная страница платформы"""
    return render(request, 'home.html')


def support(request):
    """Страница поддержки и контактов"""
    return render(request, 'support.html')


def legal_index(request):
    return render(
        request,
        'legal/index.html',
        {
            'legal_documents': LEGAL_DOCUMENTS,
        },
    )


def legal_document(request, slug):
    document = get_document(slug)
    if document is None:
        raise Http404('Документ не найден')

    return render(
        request,
        'legal/document.html',
        {
            'document': document,
            'document_slug': slug,
            'paragraphs': get_document_text(slug),
            'legal_documents': LEGAL_DOCUMENTS,
        },
    )


@login_required
@ensure_csrf_cookie
def legal_acceptance_required(request):
    if user_has_required_legal_acceptances(request.user):
        return redirect('profile')

    return render(
        request,
        'legal/acceptance_required.html',
        {
            'required_documents': get_required_documents(),
        },
    )


@login_required
@require_POST
def accept_required_legal(request):
    if request.POST.get('accept_terms') != 'on' or request.POST.get('accept_personal_data') != 'on':
        return render(
            request,
            'legal/acceptance_required.html',
            {
                'required_documents': get_required_documents(),
                'error': 'Необходимо отметить оба обязательных согласия.',
            },
            status=400,
        )

    record_required_legal_acceptances(request.user, request)
    next_url = request.POST.get('next') or 'profile'
    if next_url != 'profile' and not url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
        next_url = 'profile'
    return redirect(next_url)


@require_POST
def accept_cookie_policy(request):
    policy = get_cookie_policy()
    accepted_at = timezone.now()
    if request.user.is_authenticated:
        CookieConsent.objects.get_or_create(
            user=request.user,
            policy_version=policy['version'],
            defaults={
                'accepted_at': accepted_at,
                'ip_address': get_client_ip(request) or None,
                'user_agent': get_user_agent(request),
            },
        )

    response = JsonResponse({'ok': True, 'version': policy['version'], 'accepted_at': accepted_at.isoformat()})
    response.set_cookie(
        f'maestro_cookie_policy_{policy["version"]}',
        accepted_at.isoformat(),
        max_age=60 * 60 * 24 * 365,
        samesite='Lax',
    )
    return response


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
