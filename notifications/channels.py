from accounts.models import TelegramConnection

from .models import NotificationChannelPreference, NotificationDelivery


EMAIL_CHANNEL = NotificationDelivery.CHANNEL_EMAIL
TELEGRAM_CHANNEL = NotificationDelivery.CHANNEL_TELEGRAM


def get_active_channels(user, notification_type):
    """Return external notification channels enabled and usable for a user."""
    preference = NotificationChannelPreference.get_or_create_for(user)
    channels = set()

    if (
        preference.email_enabled
        and bool(user.email)
        and getattr(user, 'is_email_verified', False)
    ):
        channels.add(EMAIL_CHANNEL)

    if (
        preference.telegram_enabled
        and TelegramConnection.objects.filter(
            user=user,
            telegram_chat_id__isnull=False,
        ).exists()
    ):
        channels.add(TELEGRAM_CHANNEL)

    return channels
