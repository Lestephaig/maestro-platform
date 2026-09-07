from django.conf import settings

from .models import TelegramConnection
from .telegram import (
    TELEGRAM_LINK_BANNER_DISMISSED_SESSION_KEY,
    telegram_link_is_available,
)


TELEGRAM_LINK_SCREEN_URL_NAMES = {'profile'}


def telegram_link_banner(request):
    user = getattr(request, 'user', None)
    resolver_match = getattr(request, 'resolver_match', None)
    url_name = resolver_match.url_name if resolver_match else None
    should_show = (
        bool(user and user.is_authenticated)
        and telegram_link_is_available(settings.TELEGRAM_BOT_NAME)
        and url_name not in TELEGRAM_LINK_SCREEN_URL_NAMES
        and not request.session.get(TELEGRAM_LINK_BANNER_DISMISSED_SESSION_KEY, False)
        and not TelegramConnection.objects.filter(user=user).exists()
    )
    return {'show_telegram_link_banner': should_show}
