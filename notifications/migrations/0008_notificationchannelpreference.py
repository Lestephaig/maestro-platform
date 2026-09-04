import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_channel_preferences(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    TelegramConnection = apps.get_model('accounts', 'TelegramConnection')
    NotificationPreference = apps.get_model(
        'notifications',
        'NotificationPreference',
    )
    NotificationChannelPreference = apps.get_model(
        'notifications',
        'NotificationChannelPreference',
    )

    linked_user_ids = set(
        TelegramConnection.objects.values_list('user_id', flat=True)
    )
    for user_id in User.objects.values_list('id', flat=True).iterator():
        preferences = NotificationPreference.objects.filter(user_id=user_id)
        has_preferences = preferences.exists()
        email_enabled = (
            preferences.filter(email_enabled=True).exists()
            if has_preferences
            else True
        )
        telegram_enabled = (
            user_id in linked_user_ids
            and preferences.filter(telegram_enabled=True).exists()
        )
        NotificationChannelPreference.objects.create(
            user_id=user_id,
            email_enabled=email_enabled,
            telegram_enabled=telegram_enabled,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_telegramconnection_telegramlinktoken'),
        ('notifications', '0007_enable_chat_telegram_for_linked_users'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationChannelPreference',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'email_enabled',
                    models.BooleanField(
                        default=True,
                        verbose_name='Получать уведомления по email',
                    ),
                ),
                (
                    'telegram_enabled',
                    models.BooleanField(
                        default=False,
                        verbose_name='Получать уведомления в Telegram',
                    ),
                ),
                (
                    'updated_at',
                    models.DateTimeField(auto_now=True, verbose_name='Обновлено'),
                ),
                (
                    'user',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='notification_channel_preference',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Пользователь',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Настройка каналов уведомлений',
                'verbose_name_plural': 'Настройки каналов уведомлений',
            },
        ),
        migrations.RunPython(
            migrate_channel_preferences,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name='notificationpreference',
            name='email_enabled',
        ),
        migrations.RemoveField(
            model_name='notificationpreference',
            name='telegram_enabled',
        ),
    ]
