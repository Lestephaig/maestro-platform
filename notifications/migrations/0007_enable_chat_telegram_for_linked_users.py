from django.db import migrations


CHAT_MESSAGE = 'chat_message'


def enable_for_linked_users(apps, schema_editor):
    TelegramConnection = apps.get_model('accounts', 'TelegramConnection')
    NotificationPreference = apps.get_model('notifications', 'NotificationPreference')

    for user_id in TelegramConnection.objects.values_list('user_id', flat=True).iterator():
        NotificationPreference.objects.update_or_create(
            user_id=user_id,
            notification_type=CHAT_MESSAGE,
            defaults={'telegram_enabled': True},
        )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_telegramconnection_telegramlinktoken'),
        ('notifications', '0006_notification_delivery'),
    ]

    operations = [
        migrations.RunPython(enable_for_linked_users, migrations.RunPython.noop),
    ]
