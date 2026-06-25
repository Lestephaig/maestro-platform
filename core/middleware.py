from django.shortcuts import redirect
from django.urls import reverse

from .legal import user_has_required_legal_acceptances


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
