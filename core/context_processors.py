from .legal import LEGAL_DOCUMENTS, get_cookie_policy, user_has_cookie_consent


def legal_documents(request):
    cookie_policy = get_cookie_policy()
    cookie_consent_required = True
    if request.user.is_authenticated:
        cookie_consent_required = not user_has_cookie_consent(request.user)

    return {
        'legal_documents': LEGAL_DOCUMENTS,
        'cookie_policy': cookie_policy,
        'cookie_consent_required': cookie_consent_required,
    }
