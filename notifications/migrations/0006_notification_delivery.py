from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_messageattachment_alter_message_text'),
        ('notifications', '0005_notification_channel_status_and_label_update'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationpreference',
            name='telegram_enabled',
            field=models.BooleanField(default=False, verbose_name='Telegram'),
        ),
        migrations.CreateModel(
            name='NotificationDelivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('channel', models.CharField(choices=[('email', 'Email'), ('telegram', 'Telegram')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Ожидает отправки'), ('processing', 'Отправляется'), ('sent', 'Отправлено'), ('failed', 'Ошибка'), ('skipped', 'Пропущено')], default='pending', max_length=20)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('next_attempt_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notification_deliveries', to='chat.message')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notification_deliveries', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('created_at', 'id'),
                'indexes': [models.Index(fields=['status', 'next_attempt_at'], name='notificatio_status_e1aed1_idx')],
                'constraints': [models.UniqueConstraint(fields=('message', 'recipient', 'channel'), name='unique_message_recipient_channel_delivery')],
            },
        ),
    ]
