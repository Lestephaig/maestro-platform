from django.shortcuts import redirect
from django.urls import reverse

from .legal import user_has_required_legal_acceptances
from accounts.profile_completion import get_missing_profile_fields


class RequiredLegalAcceptanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._must_accept_legal(request):
            return redirect(f'{reverse("legal_acceptance_required")}?next={request.path}')
        return self.get_response(request)

    def _must_accept_legal(self, request):
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False

        path = request.path
        allowed_prefixes = (
            '/legal/',
            '/logout/',
            '/admin/',
            '/grappelli/',
            '/static/',
            '/media/',
            '/favicon.ico',
        )
        if any(path.startswith(prefix) for prefix in allowed_prefixes):
            return False

        return not user_has_required_legal_acceptances(user)


class RequiredProfileCompletionMiddleware:
    ALLOWED_PATHS = {
        '/accounts/profile/',
        '/accounts/profile/view/',
        '/accounts/profile/edit/',
        '/logout/',
    }
    ALLOWED_PREFIXES = (
        '/accounts/api/telegram/',
        '/legal/',
        '/admin/',
        '/grappelli/',
        '/static/',
        '/media/',
        '/favicon.ico',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if (
            user
            and user.is_authenticated
            and not user.is_staff
            and request.path not in self.ALLOWED_PATHS
            and not any(request.path.startswith(prefix) for prefix in self.ALLOWED_PREFIXES)
            and get_missing_profile_fields(user)
        ):
            return redirect('profile')
        return self.get_response(request)
