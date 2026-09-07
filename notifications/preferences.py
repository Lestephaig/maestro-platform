from django.db import transaction

from accounts.models import TelegramConnection

from .models import NotificationChannelPreference


CHANNEL_FIELDS = ('email_enabled', 'telegram_enabled')


class NotificationPreferenceValidationError(ValueError):
    def __init__(self, errors):
        super().__init__('Invalid notification channel preferences')
        self.errors = errors


def telegram_is_linked(user):
    return TelegramConnection.objects.filter(
        user=user,
        telegram_chat_id__isnull=False,
    ).exists()


def get_channel_settings(user):
    preference = NotificationChannelPreference.get_or_create_for(user)
    telegram_linked = telegram_is_linked(user)
    if preference.telegram_enabled and not telegram_linked:
        preference.telegram_enabled = False
        preference.save(update_fields=['telegram_enabled', 'updated_at'])

    return {
        'email_enabled': preference.email_enabled,
        'telegram_enabled': preference.telegram_enabled,
        'telegram_linked': telegram_linked,
    }


def validate_channel_updates(user, updates):
    if not isinstance(updates, dict):
        raise NotificationPreferenceValidationError({
            'body': 'Тело запроса должно быть объектом.',
        })

    unknown_fields = set(updates) - set(CHANNEL_FIELDS)
    errors = {}
    if unknown_fields:
        errors['body'] = 'Неизвестные поля: ' + ', '.join(sorted(unknown_fields)) + '.'

    values = {}
    for field in CHANNEL_FIELDS:
        if field not in updates:
            continue
        if not isinstance(updates[field], bool):
            errors[field] = 'Значение должно быть boolean.'
            continue
        values[field] = updates[field]

    if not values:
        errors['body'] = 'Укажите хотя бы один переключатель.'
    if values.get('telegram_enabled') and not telegram_is_linked(user):
        errors['telegram_enabled'] = 'Сначала привяжите аккаунт Telegram.'

    if errors:
        raise NotificationPreferenceValidationError(errors)
    return values


@transaction.atomic
def update_channel_settings(user, updates):
    values = validate_channel_updates(user, updates)
    preference = NotificationChannelPreference.get_or_create_for(user)
    changed_fields = []
    for field, value in values.items():
        if getattr(preference, field) != value:
            setattr(preference, field, value)
            changed_fields.append(field)
    if changed_fields:
        preference.save(update_fields=[*changed_fields, 'updated_at'])
    return get_channel_settings(user)
